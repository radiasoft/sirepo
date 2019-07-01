'use strict';
beforeEach(module('SirepoApp'));

describe('geometry', function() {

    it('should fail [points]', inject(function(geometry) {

        var p1 = geometry.point(0, 1);
        var p2 = geometry.point(1, 0);
        var p3 = geometry.point(0, 0, 0);

        // points have different dimension
        expect(function () {
            p1.dist(p3);
        }).toThrow();

    }));

     it('should fail [sortInDimension]: point array invalid', inject(function(geometry) {

        var p1 = geometry.point(0, 1);
        var p2 = geometry.point(1, 0);
        var p3 = geometry.point(0, 0, 0);

        var arr1 = [];
        var arr2 = [p1, p2];
        var arr3 = [p1, p3];

        // null array
        expect(function () {
            geometry.sortInDimension(null, 0, false);
        }).toThrow();

        // empty array
        expect(function () {
            geometry.sortInDimension(arr1, 0, false);
        }).toThrow();

        // points have different dimensions
        expect(function () {
            geometry.sortInDimension(arr3, 'x', false);
        }).toThrow();

    }));

   it('should pass [points]: ', inject(function(geometry) {
        var p1 = geometry.point(0, 1);
        var p2 = geometry.point(1, 0);
        expect(p1.dimension()).toBe(2);
        expect(p2.dimension()).toBe(2);

        var d1 = p1.dist(p2);
        var d2 = p2.dist(p1);

        // order of points in dist does not matter
        expect(d1).toBe(d2);

        // 3d point
        var p3 = geometry.point(0, 0, 0);
        expect(p3.dimension()).toBe(3);

        var arr1 = [p1, p2];

        var arr2 = geometry.sortInDimension(arr1, 'x', false);
        var arr3 = geometry.sortInDimension(arr1, 'y', false);
        var arr4 = geometry.sortInDimension(arr1, 'x', true);
        var arr5 = geometry.sortInDimension(arr1, 'y', true);

        // sort dimension and ordering
        expect(arr2[0].equals(p1) && arr2[1].equals(p2)).toBeTruthy();
        expect(arr5[0].equals(p1) && arr2[1].equals(p2)).toBeTruthy();
        expect(arr3[0].equals(p2) && arr3[1].equals(p1)).toBeTruthy();
        expect(arr4[0].equals(p2) && arr4[1].equals(p1)).toBeTruthy();
   }));

    it('should pass [lines]: ', inject(function(geometry) {
        var p0 = geometry.point(0, 0);
        var p1 = geometry.point(0, 1);
        var p2 = geometry.point(1, 0);
        var p3 = geometry.point(1, 1);
        var p4 = geometry.point(2, 2);

        var l1 = geometry.line(p1, p3);
        expect(l1.slope()).toBe(0);

        var l2 = geometry.line(p2, p3);
        expect(l2.slope()).toBe(Infinity);

        var i1 = l1.intersection(l2);
        var i2 = l2.intersection(l1);

        expect(i1.equals(p3)).toBeTruthy();
        expect(i2.equals(p3)).toBeTruthy();

        var l3 = geometry.line(p0, p3);
        expect(l3.slope()).toBe(1);
        expect(l3.intercept()).toBe(0);

        var l4 = geometry.line(p3, p4);
        expect(l3.equals(l4)).toBeTruthy();
    }));

     it('should pass [line segments]: ', inject(function(geometry) {

         var p0 = geometry.point(0, 0);
         var p1 = geometry.point(0, 1);
         var p2 = geometry.point(1, 0);
         var p3 = geometry.point(1, 1);
         var p4 = geometry.point(2, 2);

         var l1 = geometry.lineSegment(p1, p3);
         expect(l1.slope()).toBe(0);
         expect(l1.length()).toBe(1);

         var l2 = geometry.lineSegment(p2, p3);
         expect(l2.slope()).toBe(Infinity);

         var i1 = l1.intersection(l2);
         var i2 = l2.intersection(l1);

         expect(i1.equals(p3)).toBeTruthy();
         expect(i2.equals(p3)).toBeTruthy();
    }));


   it('should pass [rects]: ', inject(function(geometry) {
        var p1 = geometry.point(-0.5, -0.5);
        var p2 = geometry.point(0.5, 0.5);
        var p3 = geometry.point(0, 0);
        var p4 = geometry.point(1, 1);

        var r1 = geometry.rect(p1, p2);
        var b1 = r1.sides();

        var r2 = geometry.rect(p3, p4);

        expect(r1.containsPoint(p3)).toBeTruthy();
        expect(r1.containsPoint(p4)).toBeFalsy();

        var p5 = geometry.point(-1, 0);
        var p6 = geometry.point(0, 1);

        var bint1 = r1.boundaryIntersectionsWithPts(p5, p6);
        expect(bint1.length === 2).toBeTruthy();
        expect(bint1[0].equals(geometry.point(-0.5, 0.5))).toBeTruthy();
        expect(bint1[1].equals(geometry.point(-0.5, 0.5))).toBeTruthy();

        var p7 = geometry.point(-0.25, -0.25);
        var l1 = geometry.lineSegment(p3, p7);
        var l2 = geometry.lineSegment(p3, p4);
        expect(r1.containsLineSegment(l1)).toBeTruthy();
        expect(r1.containsLineSegment(l2)).toBeFalsy();

        var lArr = [l1, l2];
        var lIn = r1.segmentsInside(lArr);
        expect(lIn.length).toBe(1);
        expect(lIn[0].equals(l1)).toBeTruthy();

        expect(r1.intersectsRect(r2)).toBeTruthy();
        expect(r2.intersectsRect(r1)).toBeTruthy();

        var r3 = geometry.rect(
            geometry.point(16, 16),
            geometry.point(726, 726)
        );
        var r4 = geometry.rect(
            geometry.point(-42, 189),
            geometry.point(599, 558)
        );
        expect(r3.intersectsRect(r4)).toBeTruthy();
        expect(r4.intersectsRect(r3)).toBeTruthy();

        var r5 = geometry.rect(
            geometry.point(-0.25, -0.25),
            geometry.point(0.25, 0.25)
        );

        // r5 is entirely within r1
        expect(r1.intersectsRect(r5)).toBeFalsy();
    }));

   it('should fail [transform]: ', inject(function(geometry) {

         var m2 = [];
         var m3 = [
             [0, 1],
             [1]
         ];
         var m4 = [
             [1, 1, 1, 1],
             [2, 2, 2, 2],
             [3, 3, 3, 3],
             [4, 4, 4, 4]
         ];

        // empty matrix
        expect(function () {
            var tx = geometry.transform(m2);
        }).toThrow();

        // non-square matrix
        expect(function () {
            var tx = geometry.transform(m3);
        }).toThrow();

        // matrix too long
        expect(function () {
            var tx = geometry.transform(m4);
        }).toThrow();

   }));

   it('should pass [transform]: ', inject(function(geometry) {

       var m1 = null;
       var m2 = [
           [0, 0, 1],
           [1, 0, 0],
           [0, 1, 0]
       ];
       var m2i = [
           [0, 1, 0],
           [0, 0, 1],
           [1, 0, 0]
       ];

       var p1 = [1, 0, 0];
       var pt1 = geometry.pointFromArr(p1);
       var p2 = [0, 1, 0];
       var pt2 = geometry.pointFromArr(p2);
       var p3 = [0, 0, 1];
       var pt3 = geometry.pointFromArr(p3);


       // identity
       var tx1 = geometry.transform(m1);
       var px1 = tx1.doTransform(p1);
       expect(px1[0] === p1[0] && px1[1] === p1[1] && px1[2] === p1[2]).toBeTruthy();
       expect(tx1.det()).toBe(1);

       var ptx1 = tx1.doTX(pt1);
       expect(pt1.equals(ptx1)).toBeTruthy();

       // x -> y, y -> z, z -> x
       var tx2 = geometry.transform(m2);
       //console.log('tx2', tx2.str());
       var px2 = tx2.doTransform(p1);
       //console.log('p1', p1, 'px2', px2, 'p2', p2);
       expect(px2[0] === p2[0] && px2[1] === p2[1] && px2[2] === p2[2]).toBeTruthy();

       var ptx2 = tx2.doTX(pt1);
       expect(pt2.equals(ptx2)).toBeTruthy();

       var tx2i = geometry.transform(m2i);
       //console.log('tx2 inv', tx2i.str());

       // tranform composed with inverse == identity
       var tx2_tx2i = tx2.compose(tx2i);
       //console.log('tx2 comp tx2 inv', tx2_tx2i.str());
       px1 = tx2_tx2i.doTransform(p1);
       expect(px1[0] === p1[0] && px1[1] === p1[1] && px1[2] === p1[2]).toBeTruthy();

       var mfib = [
           [0, 1, 2],
           [3, 5, 8],
           [13, 21, 34]
       ];
       var txfib = geometry.transform(mfib);
       expect(txfib.det()).toBe(-2);

       var tx3 = geometry.transform([
           [1, 1, 0],
           [0, 1, 0],
           [1, 0, 1]
       ]);
       var tx4 = geometry.transform([
           [0, 1, 0],
           [1, 0, 0],
           [0, 1, 1]
       ]);
       var m34 = [
           [1, 1, 0],
           [1, 0, 0],
           [0, 2, 1]
       ];
       var m43 = [
           [0, 1, 0],
           [1, 1, 0],
           [1, 1, 1]
       ];

       var tx34 = tx3.compose(tx4);
       var tx43 = tx4.compose(tx3);
       expect(tx34.equals(geometry.transform(m34))).toBeTruthy();
       expect(tx43.equals(geometry.transform(m43))).toBeTruthy();

   }));

   it('should pass [minors]: ', inject(function(geometry) {

       var m1 = [
           [1, 2, 3],
           [3, 4, 5],
           [5, 6, 4]
       ];
       var mn00 = [
           [4, 5],
           [6, 4]
       ];
       var mn01 = [
           [3, 5],
           [5, 4]
       ];
       expect(geometry.matrixEquals(mn00, geometry.matrixMinor(m1, 0, 0))).toBeTruthy();
       expect(geometry.matrixEquals(mn01, geometry.matrixMinor(m1, 0, 1))).toBeTruthy();

   }));

   it('should pass [invert]: ', inject(function(geometry) {

       var I = [
           [1, 0, 0],
           [0, 1, 0],
           [0, 0, 1]
       ];
       var tI = geometry.transform(I);
       var IInv = geometry.matrixInvert(I);
       var tIINV = geometry.transform(IInv);

       // identity is its own inverse
       expect(geometry.matrixEquals(I, IInv)).toBeTruthy();

       var m1 = [
           [1, 0, 3],
           [4, 5, 6],
           [7, 8, 9]
       ];
       var m1Inv = geometry.matrixInvert(m1);
       var m2 = [
           [0.25, -2, 1.25],
           [-0.5, 1, -0.5],
           [0.25, 2/3, -5/12]
       ];
       expect(geometry.matrixEquals(m1Inv, m2)).toBeTruthy();


   }));

});
