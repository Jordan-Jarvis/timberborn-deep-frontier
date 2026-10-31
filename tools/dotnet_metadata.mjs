// Minimal ECMA-335 reader: the type definitions (namespace, name) of a managed DLL.
// Enough for dependency checks (tools/validate_mod_dependencies.mjs); it reads the
// PE section table, the CLI header, the metadata root, the #~ table stream and the
// #Strings heap, and the Module, TypeRef and TypeDef tables (ECMA-335 II.22, II.24).
import {readFile} from 'node:fs/promises';

const MODULE = 0x00, TYPEREF = 0x01, TYPEDEF = 0x02, FIELD = 0x04, METHODDEF = 0x06,
  MODULEREF = 0x1a, TYPESPEC = 0x1b, ASSEMBLYREF = 0x23;

export async function readTypeDefinitions(path) {
  const b = await readFile(path);
  const fail = (what) => { throw new Error(`${path}: ${what}`); };
  if (b.readUInt16LE(0) !== 0x5a4d) fail('not a PE file');
  const pe = b.readUInt32LE(0x3c);
  if (b.readUInt32LE(pe) !== 0x4550) fail('no PE signature');
  const sections = b.readUInt16LE(pe + 6);
  const optionalSize = b.readUInt16LE(pe + 20);
  const optional = pe + 24;
  const magic = b.readUInt16LE(optional);
  const directories = optional + (magic === 0x20b ? 112 : magic === 0x10b ? 96 : fail(`unknown optional header ${magic}`));
  const cliRva = b.readUInt32LE(directories + 14 * 8);
  if (!cliRva) fail('not a managed assembly');
  const table = optional + optionalSize;
  const offset = (rva) => {
    for (let i = 0; i < sections; i++) {
      const s = table + i * 40;
      const va = b.readUInt32LE(s + 12), size = Math.max(b.readUInt32LE(s + 8), b.readUInt32LE(s + 16));
      if (rva >= va && rva < va + size) return rva - va + b.readUInt32LE(s + 20);
    }
    return fail(`RVA ${rva} outside every section`);
  };
  const cli = offset(cliRva);
  const root = offset(b.readUInt32LE(cli + 8));
  if (b.readUInt32LE(root) !== 0x424a5342) fail('no metadata signature');
  let p = root + 16 + b.readUInt32LE(root + 12);
  const streamCount = b.readUInt16LE(p + 2);
  p += 4;
  const streams = {};
  for (let i = 0; i < streamCount; i++) {
    const start = b.readUInt32LE(p), size = b.readUInt32LE(p + 4);
    let end = p + 8;
    while (b[end]) end++;
    streams[b.toString('ascii', p + 8, end)] = {start: root + start, size};
    p = (end + 4) & ~3;
  }
  const tilde = streams['#~'] ?? streams['#-'] ?? fail('no table stream');
  const strings = streams['#Strings'] ?? fail('no #Strings heap');
  const heapSizes = b[tilde.start + 6];
  const valid = b.readBigUInt64LE(tilde.start + 8);
  const rows = new Array(64).fill(0);
  let q = tilde.start + 24;
  for (let t = 0; t < 64; t++) if (valid & (1n << BigInt(t))) { rows[t] = b.readUInt32LE(q); q += 4; }
  const str = heapSizes & 1 ? 4 : 2, guid = heapSizes & 2 ? 4 : 2;
  const index = (t) => rows[t] < 0x10000 ? 2 : 4;
  const coded = (bits, tables) => Math.max(...tables.map((t) => rows[t])) < (1 << (16 - bits)) ? 2 : 4;
  const moduleRow = 2 + str + 3 * guid;
  const typeRefRow = coded(2, [MODULE, MODULEREF, ASSEMBLYREF, TYPEREF]) + 2 * str;
  const extendsSize = coded(2, [TYPEDEF, TYPEREF, TYPESPEC]);
  const typeDefRow = 4 + 2 * str + extendsSize + index(FIELD) + index(METHODDEF);
  const read = (at, size) => size === 2 ? b.readUInt16LE(at) : b.readUInt32LE(at);
  const string = (i) => { const s = strings.start + i; let e = s; while (b[e]) e++; return b.toString('utf8', s, e); };
  let at = q + rows[MODULE] * moduleRow + rows[TYPEREF] * typeRefRow;
  const types = [];
  for (let i = 0; i < rows[TYPEDEF]; i++, at += typeDefRow) {
    const name = string(read(at + 4, str)), namespace = string(read(at + 4 + str, str));
    if (name !== '<Module>') types.push({namespace, name});
  }
  return types;
}
