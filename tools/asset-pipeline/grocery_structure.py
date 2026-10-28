"""Grocery structure: full-width storefront and rear supply gallery."""
ORIGIN=[.4,0,0]
ROOMS={
    'GroundHall':[2,3,0,7,6,2], 'MiddleHall':[2,3,2,7,6,4],
    'UpperHall':[2,3,4,7,6,6], 'EntranceVestibule':[1,2,0,3,4,2],
    'RoofStairhead':[6,4,6,8,5,8],
}
EXTERIOR_WALLS={
    'GroundHall':{'front':[(3,7)],'back':[(2,7)],'left':[(4,6)],'right':[(3,6)]},
    'MiddleHall':{'front':[(2,7)],'back':[(2,7)],'left':[(3,6)],'right':[(3,6)]},
    'UpperHall':{'front':[(2,7)],'back':[(2,7)],'left':[(3,6)],'right':[(3,6)]},
    'EntranceVestibule':{'front':[(1,3)],'back':[(1,2)],'left':[(2,4)],'right':[(2,3)]},
}
PLATFORMS={
    'ShopFront':[1,1,0,7,3,2], 'ShopSide':[7,2,0,8,7,2], 'ShopRear':[2,6,0,7,7,2],
    'UpperShopFront':[1,1,2,7,3,4], 'UpperShopSide':[7,2,2,8,7,4], 'UpperShopRear':[2,6,2,7,7,4],
    'RoofTerraceInner':[7,3,4,8,6,6], 'RoofTerraceOuter':[8,3,5,10,6,6],
}
SUPPORTS={
    'ShopFront':[([1,1],[-1,-1],0),([4,1],[1,-1],0),([6,1],[1,-1],0)],
    'ShopSide':[([7,2],[1,-1],0),([7,6],[1,1],0)], 'ShopRear':[([2,6],[-1,1],0)],
    'UpperShopFront':[([1,1],[-1,-1],2),([4,1],[1,-1],2),([6,1],[1,-1],2)],
    'UpperShopSide':[([7,2],[1,-1],2),([7,6],[1,1],2)], 'UpperShopRear':[([2,6],[-1,1],2)],
    'RoofTerraceInner':[([7,3],[1,-1],4),([7,5],[1,1],4)], 'RoofTerraceOuter':[],
}
DOORS={
    'GroundDoor':{'position':[2.5,2,0],'outward':[0,-1],'width':1.0},
    'MiddleDoor':{'position':[4.5,3,2],'outward':[0,-1],'width':1.0},
    'UpperDoor':{'position':[4.5,3,4],'outward':[0,-1],'width':1.0},
    'RoofTerraceDoor':{'position':[8,4.5,6],'outward':[1,0],'width':1.0},
}
RESERVATIONS=[
    [3,1,0,7,2,2], [7,3,0,8,6,1],
    [2,3,6,7,6,7], [3,3,7,6,6,9], [6,5,6,7,6,9],
    [8,5,6,10,6,7], [6,6,6,7,7,8],
]
