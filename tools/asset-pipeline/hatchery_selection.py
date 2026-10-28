"""Picking follows real nursery equipment, not empty platform corner cells.

Boxes are native grid coordinates (source + SOURCE_ORIGIN x 0.2, y 0.75,
z + 1). 2026-10-26: compact 7x7 grid (x moved by -1); the net drying frame
boxes behind the pens went with their frames (removed 2026-10-22)."""
def box(center,size):return {'center':list(center),'size':list(size)}
def parts():
    equipment=[]
    for x0,y0,x1,y1 in ((.22,3.58,1.70,6.02),(2.80,3.58,4.25,6.02)):
        for x in (x0,x1):equipment.append(box((x+.2,(y0+y1)/2+.75,.625),(.13,y1-y0+.13,.87)))
        for y in (y0,y1):equipment.append(box(((x0+x1)/2+.2,y+.75,.625),(x1-x0+.13,.13,.87)))
        equipment.append(box((x0+.40,(y0+y1)/2+.75,1.3575),(.36,.47,.355)))
    # Four real service canopy posts, not a box across the open canopy bay.
    for x in (4.75,6.35):
        for y in (1.51,3.37):equipment.append(box((x,y,1.86),(.28,.28,1.72)))
    equipment.extend([
        box((5.55,2.25,1.41),(1.05,.72,.82)),
        box((5.55,2.25,1.86),(1.13,.80,.08)),
        box((5.55,2.25,2.08),(.88,.56,.56)),
        box((5.55,2.885,2.06),(.11,.54,.11)),
        box((5.025,3.1,2.06),(1.16,.11,.11)),
        box((4.5,3.1,1.68),(.11,.11,.87)),
        box((6.17,2.25,1.4),(.21,.11,.11)),
        box((6.22,2.915,1.4),(.11,1.44,.11)),
        box((3.85,.75,1.2322),(.369,.369,.4644)),
        box((6.20,1.,1.1935),(.3074,.3075,.387)),
        box((5.5299,.8423,1.3845),(.466,.4815,.7693)),
    ])
    for x in (2.65,3.25):equipment.append(box((x,.947,1.335),(.37,.30,.55)))
    roofs=[]
    for x0,y0,x1,y1,bottom,eave,ridge in ((-.1,.9,4.1,3.1,3.,3.08,4.18),(4.55,1.29,6.54,3.56,2.75,2.85,3.43)):
        mid=(x0+x1)/2;half=(x1-x0)/2
        for i in range(16):
            a=x0+i*(x1-x0)/16;b=x0+(i+1)*(x1-x0)/16
            top=eave+(ridge-eave)*(1-max(abs(a-mid),abs(b-mid))/half)
            roofs.append(box(((a+b)/2,(y0+y1)/2,(bottom+top)/2),(b-a,y1-y0,top-bottom)))
    return [{'id':'RetainedEquipment','kind':'equipment','pickingBoxes':equipment},
            {'id':'RoofSelection','kind':'roof','pickingBoxes':roofs}]
