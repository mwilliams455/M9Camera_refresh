import unittest,struct,ctypes
import numpy as np
from shaded_noise import native,reference,reference_strips,gain_image,parse_maps,ROOT

P=np.array([[.0004,.000001],[.00038,.0000008],[.00039,.0000009],[.00042,.0000011]])
B=np.array([64.,65.,66.,67.])*16
GEO=np.array([.25,.2,0.,0.])

class ShadedTests(unittest.TestCase):
    def test_native_reference_strips_and_geometry(self):
        rng=np.random.default_rng(2193)
        for shape in [(17,19),(135,143),(141,24)]:
            for kind in ['unity','smooth','strong']:
                raw=rng.integers(1500,2500,shape,dtype=np.uint16)
                grids=np.ones((4,5,6),np.float32)
                if kind=='smooth':grids+=rng.random(grids.shape).astype(np.float32)*.5
                if kind=='strong':grids=rng.uniform(.4,5,grids.shape).astype(np.float32)
                geo=GEO if kind!='strong' else np.array([.15,.12,.1,-.1])
                for mode in [0,1,2]:
                    for strength in [0,1,2,4]:
                        with self.subTest(shape=shape,kind=kind,mode=mode,k=strength):
                            np.testing.assert_array_equal(native(raw,mode,strength,P,B,16368,grids,geo),
                                                          reference(raw,mode,strength,P,B,16368,grids,geo))

    def test_noop_and_constant_phase(self):
        yy,xx=np.indices((136,142));phase=(yy%2)*2+xx%2
        raw=np.array([1904,2304,1808,4000],dtype=np.uint16)[phase]
        grids=np.broadcast_to(np.array([1,2,4,.5],np.float32)[:,None,None],(4,2,2)).copy()
        for mode in [0,1,2]:
            np.testing.assert_array_equal(native(raw,mode,2,P,B,16368,grids,np.ones(4)),raw)
        rng=np.random.default_rng(2);raw=rng.integers(0,16369,raw.shape,dtype=np.uint16)
        before=raw.copy()
        for mode in [0,1,2]:np.testing.assert_array_equal(native(raw,mode,0,P,B,16368,grids,GEO),raw)
        np.testing.assert_array_equal(raw,before)

    def test_fractional_gain_flat_field_regression(self):
        # Before residual transfer: 1,015 pixels became 1903 instead of 1904.
        a=np.full((33,39),1904,np.uint16);b=np.full(4,1024.)
        for gain in [.5009765625,1.0009765625,1.013,2.6731,4.818359375]:
            grids=np.full((4,2,2),gain,np.float32)
            for mode in [1,2]:
                for k in [1,2,4]:np.testing.assert_array_equal(native(a,mode,k,P,b,16368,grids,GEO),a)

    def test_stripped_reference_matches_whole(self):
        rng=np.random.default_rng(51)
        for shape in [(137,139),(141,149)]:
            a=rng.integers(2300,2500,shape,dtype=np.uint16);grids=rng.uniform(.8,3,(4,5,6)).astype(np.float32)
            for mode in [1,2]:
                whole,d=reference(a,mode,2,P,B,16368,grids,GEO,True)
                striped,s=reference_strips(a,mode,2,P,B,16368,grids,GEO)
                np.testing.assert_array_equal(whole,striped)
                np.testing.assert_array_equal(d['target'].astype(np.float32),s['target'])

    def test_phase_isolation(self):
        rng=np.random.default_rng(35);a=rng.integers(1900,2100,(137,143),dtype=np.uint16)
        g=np.ones((4,5,6),np.float32);b=a.copy();b[1::2,::2]+=100
        for mode in [1,2]:
            out1=native(a,mode,2,P,B,16368,g,GEO);out2=native(b,mode,2,P,B,16368,g,GEO)
            for y,x in [(0,0),(0,1),(1,1)]:np.testing.assert_array_equal(out1[y::2,x::2],out2[y::2,x::2])

    def test_censoring_guards_and_borders(self):
        rng=np.random.default_rng(61);a=rng.integers(4900,5100,(139,145),dtype=np.uint16)
        a[50,50]=9000;a[80,90]=500;a[110,110]=16368
        grids=np.full((4,5,6),2,np.float32)
        for mode in [1,2]:
            out,diag=reference(a,mode,3,P,B,16368,grids,GEO,True)
            np.testing.assert_array_equal(out,native(a,mode,3,P,B,16368,grids,GEO))
            r=2*mode
            for y,x in [(50,50),(80,90),(110,110)]:
                for dy in range(-r,r+1,2):
                    for dx in range(-r,r+1,2):self.assertEqual(out[y+dy,x+dx],a[y+dy,x+dx])
            np.testing.assert_array_equal(out[:r],a[:r]);np.testing.assert_array_equal(out[-r:],a[-r:])
            np.testing.assert_array_equal(out[:,:r],a[:,:r]);np.testing.assert_array_equal(out[:,-r:],a[:,-r:])

    def test_variance_scales_by_gain_squared(self):
        a=np.full((33,39),2600,np.uint16);b=np.full(4,1024.)
        for mode,factor in [(1,41/64),(2,945/1024)]:
            for gain in [.5,1,2,4]:
                grids=np.full((4,2,2),gain,np.float32)
                _,d=reference(a,mode,2,P,b,16368,grids,GEO,True)
                yy,xx=np.indices(d['residual_variance'].shape);phase=(yy%2)*2+xx%2
                expected=gain*gain*15344**2*(P[phase,0]*((2600-1024)/15344)+P[phase,1])*factor
                np.testing.assert_allclose(d['residual_variance'],expected,rtol=2e-15)

    def test_inverse_storage_error_bound(self):
        rng=np.random.default_rng(818);a=rng.integers(2300,2500,(139,141),dtype=np.uint16)
        g=rng.uniform(.5,3,(4,5,6)).astype(np.float32)
        for mode in [1,2]:
            out,d=reference(a,mode,3,P,B,16368,g,GEO,True)
            yy,xx=np.indices(a.shape);b=B[(yy%2)*2+xx%2]
            projected=b+d['gain']*(out.astype(float)-b)
            error=np.abs(projected-d['target'])
            self.assertTrue(np.all(error<=.5000000001*d['gain']))

    def test_post_shading_differs_from_pre_shading(self):
        # Alternating same-phase values plus a spatial gain gradient make
        # the two orders measurably different (a regression discriminator).
        a=np.full((35,39),2400,np.uint16);yy,xx=np.indices(a.shape)
        a=((a.astype(int)+((xx//2)%2)*80)).astype(np.uint16)
        g=np.linspace(1,2,16,dtype=np.float32).reshape(4,2,2)
        aware=native(a,1,4,P,B,16368,g,GEO)
        pre=native(a,1,4,P,B,16368,np.ones_like(g),GEO)
        self.assertGreater(np.count_nonzero(aware!=pre),100)

    def test_gain_interpolation_corners_and_phase(self):
        grids=np.array([[[1,2],[3,4]]],np.float32).repeat(4,0)
        grids+=np.arange(4,dtype=np.float32)[:,None,None]*10
        got=gain_image((6,8),grids,np.array([1,1,0,0],float))
        for y,x in [(0,0),(0,1),(1,0),(1,1),(4,6),(5,7)]:
            c=(y%2)*2+x%2;fy=(y+.5)/6;fx=(x+.5)/8
            expected=1+2*fy+fx+c*10
            self.assertAlmostEqual(got[y,x],expected,places=13)

    def test_invalid_inputs(self):
        a=np.full((17,19),2400,np.uint16);g=np.ones((4,2,2),np.float32)
        for bad in [0,np.nan,65]:
            grids=g.copy();grids[0,0,0]=bad
            with self.assertRaises(ValueError):native(a,1,2,P,B,16368,grids,GEO)
        for bad in [np.zeros(4),np.array([1,1,np.nan,0])]:
            with self.assertRaises(ValueError):native(a,1,2,P,B,16368,g,bad)
        with self.assertRaises(ValueError):parse_maps(b'\0\0\0\0',(17,19))

if __name__=='__main__':unittest.main(verbosity=2)
