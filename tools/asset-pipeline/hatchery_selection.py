"""Picking follows real nursery equipment, not empty platform corner cells.

Boxes are native grid coordinates (source + SOURCE_ORIGIN x 0.2, y 0.75,
z + 1). 2026-10-26: compact 7x7 grid (x moved by -1); the net drying frame
boxes behind the pens went with their frames (removed 2026-10-22).
2026-10-30: one-layer headhouse and pump canopy under flat roofs; the
filter machinery sits lower."""
def box(center,size):return {'center':list(center),'size':list(size)}
def parts():
    # 2026-11-01 second shrink pass (7x7 -> 5x5): 2x2 pens at native y 3..5,
    # the 2x2 pump canopy at x 3..5 with its machinery 1.5 west, and the
    # 3-wide headhouse. The two stale bank-row barrel boxes (barrels removed
    # 2026-10-22) and the second front-window box went.
    equipment=[]
    for x0,y0,x1,y1 in ((.22,2.58,1.70,4.02),(2.80,2.58,4.25,4.02)):
        for x in (x0,x1):equipment.append(box((x+.2,(y0+y1)/2+.75,.625),(.13,y1-y0+.13,.87)))
        for y in (y0,y1):equipment.append(box(((x0+x1)/2+.2,y+.75,.625),(x1-x0+.13,.13,.87)))
        equipment.append(box((x0+.40,(y0+y1)/2+.75,1.3575),(.36,.47,.355)))
    # Four real service canopy posts, not a box across the open canopy bay.
    for x in (3.25,4.75):
        for y in (1.51,2.81):equipment.append(box((x,y,1.40),(.28,.28,.80)))
    equipment.extend([
        box((4.05,2.17,1.13),(1.05,.72,.26)),
        box((4.05,2.17,1.29),(1.13,.80,.06)),
        box((4.05,2.17,1.56),(.88,.52,.52)),
        box((4.05,2.56,1.56),(.11,.25,.11)),
        box((3.60,2.63,1.56),(1.01,.11,.11)),
        box((3.15,2.63,1.43),(.11,.11,.37)),
        box((4.76,2.17,1.4),(.39,.11,.11)),
        box((4.90,2.42,1.4),(.11,.61,.11)),
        box((4.4999,.8423,1.3845),(.466,.4815,.7693)),
    ])
    equipment.append(box((2.65,.947,1.335),(.37,.30,.55)))
    # Flat roofs: the headhouse slab on its tile lines and the pump canopy's
    # slab with its edge beams.
    roofs=[box((1.5,2.,1.93),(3.,2.,.14)),
           box((4.0,2.12,1.94),(1.90,1.66,.28))]
    return [{'id':'RetainedEquipment','kind':'equipment','pickingBoxes':equipment},
            {'id':'RoofSelection','kind':'roof','pickingBoxes':roofs}]
