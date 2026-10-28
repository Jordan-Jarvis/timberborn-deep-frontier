"""Read-only scope-preservation gate for the targeted Hospital workbook edit."""
import json
import sys
from pathlib import Path
from xml.etree.ElementTree import tostring

from openpyxl import load_workbook


def xml(value):
    return tostring(value.to_tree(), encoding='unicode')


def style(cell):
    return [xml(cell.font), xml(cell.fill), xml(cell.border), xml(cell.alignment),
            xml(cell.protection), cell.number_format]


def snapshot(path):
    with Path(path).open('rb') as stream:
        book = load_workbook(stream, data_only=False)
    sheets = {}
    for sheet in book:
        cells = {}
        for row in sheet:
            for cell in row:
                if cell.value is not None or cell.has_style:
                    cells[cell.coordinate] = {
                        'value': cell.value, 'type': cell.data_type, 'style': style(cell),
                        'comment': None if cell.comment is None else [cell.comment.author, cell.comment.text],
                        'hyperlink': None if cell.hyperlink is None else xml(cell.hyperlink),
                    }
        sheets[sheet.title] = {
            'cells': cells,
            'dimensions': [sheet.max_row, sheet.max_column],
            'rows': {str(k): [d.height, d.hidden, d.outlineLevel, d.collapsed] for k, d in sheet.row_dimensions.items()},
            'columns': {str(k): [d.min, d.max, d.width, d.hidden, d.outlineLevel, d.collapsed] for k, d in sheet.column_dimensions.items()},
            'merges': sorted(str(r) for r in sheet.merged_cells.ranges),
            'freeze': sheet.freeze_panes,
            'gridlines': sheet.sheet_view.showGridLines,
            'state': sheet.sheet_state,
            'tables': {name: xml(sheet.tables[name]) for name in sheet.tables},
            'validation': xml(sheet.data_validations),
            'conditionalFormatting': [[str(key.sqref), [xml(rule) for rule in rules]] for key, rules in sheet.conditional_formatting._cf_rules.items()],
            'protection': xml(sheet.protection),
            'autofilter': xml(sheet.auto_filter),
            'printArea': str(sheet.print_area),
            'printTitles': sheet.print_titles,
            'charts': len(sheet._charts),
            'images': len(sheet._images),
        }
    return {'order': book.sheetnames, 'sheets': sheets,
            'definedNames': {name: xml(value) for name, value in book.defined_names.items()},
            'calculation': None if book.calculation is None else xml(book.calculation)}


def main():
    original_path, candidate_path, changes_path, report_path = map(Path, sys.argv[1:])
    before, after = snapshot(original_path), snapshot(candidate_path)
    expected = {(x['sheet'], x['address']): x for x in json.loads(changes_path.read_text())}
    changes = []
    errors = []
    for key in ['order', 'definedNames', 'calculation']:
        if before[key] != after[key]:
            errors.append({'feature': key, 'before': before[key], 'after': after[key]})
    for name in before['order']:
        left, right = before['sheets'][name], after['sheets'][name]
        for key in left:
            if key != 'cells' and left[key] != right[key]:
                errors.append({'sheet': name, 'feature': key, 'before': left[key], 'after': right[key]})
        for coordinate in set(left['cells']) | set(right['cells']):
            old, new = left['cells'].get(coordinate), right['cells'].get(coordinate)
            if old == new:
                continue
            entry = {'sheet': name, 'address': coordinate, 'before': old, 'after': new}
            if (name, coordinate) not in expected:
                errors.append(entry)
                continue
            allowed = expected[(name, coordinate)]
            if old['value'] != allowed['before'] or new['value'] != allowed['after']:
                errors.append(entry)
            elif {k: v for k, v in old.items() if k not in ['value', 'type']} != {k: v for k, v in new.items() if k not in ['value', 'type']}:
                errors.append(entry)
            else:
                changes.append({'sheet': name, 'address': coordinate, 'before': old['value'], 'after': new['value']})
    if len(changes) != len(expected):
        errors.append({'expectedChanges': len(expected), 'actualChanges': len(changes)})
    # None of the edited Hospital catalogue fields feed the workbook's existing
    # eleven formulas. Their evaluated results must survive recalculation too.
    with original_path.open('rb') as stream:
        original_results = load_workbook(stream, data_only=True)
    with candidate_path.open('rb') as stream:
        candidate_results = load_workbook(stream, data_only=True)
    formula_results = []
    for name, sheet in before['sheets'].items():
        for address, cell in sheet['cells'].items():
            if cell['type'] != 'f':
                continue
            old = original_results[name][address].value
            new = candidate_results[name][address].value
            formula_results.append({'sheet': name, 'address': address, 'before': old, 'after': new})
            if old != new or new is None:
                errors.append({'sheet': name, 'address': address, 'feature': 'formula result', 'before': old, 'after': new})
    report = {'sheets': len(before['order']), 'changedCells': changes,
              'recalculatedFormulaResults': formula_results, 'unexpectedChanges': errors}
    report_path.write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({'sheets': len(before['order']), 'changedCells': len(changes), 'unexpectedChanges': len(errors)}))
    if errors:
        raise SystemExit(f'Workbook preservation failed; details: {report_path}')


if __name__ == '__main__':
    main()
