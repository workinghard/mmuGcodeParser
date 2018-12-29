//
// Multi Material Test Object
// 
// Nikolai Rinas - 22/12/2018
//

$fn = 180;

nozzle = 0.4;
thinWall = nozzle*2;

print = "all";
//print = "base";
//print = "windows";
//print = "tubes";

baseWidth = 38;
baseHeight = 28;
baseDepth = thinWall*3;

windowHeightOffset = 4;
windowWidthOffset = 4;
windowWidth = 10;
windowHeight = 10;
windowDepth = thinWall;
windowInlay = 3;
firstWindowX = 8;
firstWindowY = 3;
firstWindowDepth = nozzle;
secondWindowX = firstWindowX * 2 + windowWidthOffset;
secondWindowY = firstWindowY;
thirdWindowX = firstWindowX;
thirdWindowY = firstWindowY+ windowHeight/1.3 + windowHeightOffset;
thirdWindowDepth = firstWindowDepth;
fourthWindowX = secondWindowX;
fourthWindowY = thirdWindowY;

towerDiameter = 10;
towerYOffset = 2;
towerHeight = baseHeight - 6;

leftTowerX = 0;
leftTowerY = towerYOffset;
rightTowerX = baseWidth;
rightTowerY = towerYOffset;

towerBaseHeight = towerYOffset + 2;
towerBaseDiameter = towerDiameter*1.5;
leftTowerBaseX = 0;
leftTowerBaseY = 0;
rightTowerBaseX = baseWidth;
rightTowerBaseY = 0;
leftTowerTopX = 0;
leftTowerTopY = towerHeight + towerYOffset;
rightTowerTopX = baseWidth;
rightTowerTopY = towerHeight + towerYOffset;

barWidth = 2.5;
barHeight = baseWidth - towerDiameter;

module windowFrame(x,y,width=thinWall) {
  translate([x,thinWall,y]){
    cube([windowWidth,width,windowHeight], center=false);
  }
}

module placeWindow(x,y,width=thinWall) {
    windowFrame(x,y,width);
    // Cut for the first window
    translate([x+(windowInlay/2),-1,y+(windowInlay/2)]) {
      cube([windowWidth-windowInlay,baseDepth+2,windowHeight-windowInlay], center=false);
    }
}

module placeTower(x,y) {
  translate([x,0,y]) {
    cylinder(towerHeight, d=towerDiameter, center=false);
  }
}

module placeCrossBeam(d,height) {
   translate([height/5.5,-2,baseHeight-d/1.9]) {
     rotate([0,90,0]) {
      //cylinder(height,d=d,center=false);
       cube([d/1.5,d/2,height], center=false);
    }
  } 
}

module placeTowerFrame(x,y) {
  translate([x,0,y]) {
    cylinder(towerBaseHeight, d=towerBaseDiameter, center=false);
  }
  if ( y == 0 ) {
    translate([x,0,y+towerBaseHeight]) {
      cylinder(towerBaseHeight*2,towerBaseDiameter/2,0, center=false);
    }
  }else{
    translate([x,0,y-towerBaseHeight*2]) {
      cylinder(towerBaseHeight*2,0,towerBaseDiameter/2, center=false);
    }    
  }
}

module plaBase() {
  union() {
    difference(){
      cube([baseWidth,baseDepth,baseHeight], center=false);
      placeWindow(firstWindowX, firstWindowY, firstWindowDepth);
      placeWindow(secondWindowX, secondWindowY);
      placeWindow(thirdWindowX, thirdWindowY, thirdWindowDepth);
      placeWindow(fourthWindowX, fourthWindowY);
      placeTower(leftTowerX, leftTowerY);
      placeTower(rightTowerX, rightTowerY);
    }
    difference() {
      placeTowerFrame(leftTowerBaseX, leftTowerBaseY);
      placeTower(leftTowerX, leftTowerY);
    }
    difference() {
      placeTowerFrame(rightTowerBaseX, rightTowerBaseY);
      placeTower(rightTowerX, rightTowerY);
    }
    difference() {
      placeTowerFrame(leftTowerTopX, leftTowerTopY);
      placeTower(leftTowerX, leftTowerY);
      placeCrossBeam(barWidth,barHeight);
    }
    difference() {
      placeTowerFrame(rightTowerTopX, rightTowerTopY);
      placeTower(rightTowerX, rightTowerY);
      placeCrossBeam(barWidth,barHeight);
    }
  }
}

module petgWindows() {
  windowFrame(firstWindowX, firstWindowY, firstWindowDepth);
  windowFrame(secondWindowX, secondWindowY);
  windowFrame(thirdWindowX, thirdWindowY, thirdWindowDepth);
  windowFrame(fourthWindowX, fourthWindowY);
}

module absTower() {
  placeTower(leftTowerX, leftTowerY);
  placeTower(rightTowerX, rightTowerY);  
}

if ( print == "base" || print == "all" ) {
  color("lime"){
    plaBase();
  }
}
if ( print == "windows" || print == "all" ) {
  color("LightBlue", alpha = 0.5){
    petgWindows();
  }
}
if ( print == "tubes" || print == "all" ) {
  color("red") {
    absTower();
    placeCrossBeam(barWidth,barHeight);
  }
}