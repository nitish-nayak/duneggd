#!/usr/bin/env python
'''
Arapuca builder for DUNE FD-VD
'''

import gegede.builder
from utils import *

class ArapucaBuilder(gegede.builder.Builder):
    def configure(self, **kwds):
        if not set(kwds).issubset(globals.Arapuca): # no unknown keywords
            msg = 'Unknown parameter in: "%s"' % (', '.join(sorted(kwds.keys())), )
            raise ValueError(msg)

        # The builder hierarchy takes care of all the configuration parameters
        globals.Arapuca = kwds

    def construct(self, geom):
        # for leaf builders, get the rest of the derived global parameters
        globals.SetDerived()
        # define all the shapes
        a_out = (globals.get("ArapucaOut_x"), globals.get("ArapucaOut_y"), globals.get("ArapucaOut_z"))
        a_acc = (globals.get("ArapucaAcceptanceWindow_x"),
                 globals.get("ArapucaAcceptanceWindow_y"),
                 globals.get("ArapucaAcceptanceWindow_z"))

        arapucaEnclosureBox = geom.shapes.Box('ArapucaEnclosure',
                                              dx = 0.5*a_out[0],
                                              dy = 0.5*a_out[1],
                                              dz = 0.5*a_out[2])
        arapucaOutBox = geom.shapes.Box('ArapucaOut',
                                        dx = 0.5*a_out[0] - Q('0.025cm'),
                                        dy = 0.5*a_out[1] - Q('0.025cm'),
                                        dz = 0.5*a_out[2] - Q('0.025cm'))
        arapucaInBox = geom.shapes.Box('ArapucaIn',
                                       dx = 0.5*globals.get("ArapucaIn_x"),
                                       dy = 0.5*a_out[1],
                                       dz = 0.5*globals.get("ArapucaIn_z"))
        arapucaWallsBox = geom.shapes.Boolean('ArapucaWalls',
                                              type = 'subtraction',
                                              first = arapucaOutBox,
                                              second = arapucaInBox,
                                              pos = geom.structure.Position('posArapucaSub',
                                                                            x = Q('0cm'),
                                                                            y = 0.5*a_out[1],
                                                                            z = Q('0cm'))
                                              )

        arapucaAccBox = geom.shapes.Box('ArapucaAcceptanceWindow',
                                        dx = 0.5*a_acc[0],
                                        dy = 0.5*a_acc[1],
                                        dz = 0.5*a_acc[2])
        arapucaDoubleInBox = geom.shapes.Box('ArapucaDoubleIn',
                                             dx = 0.5*globals.get("ArapucaIn_x"),
                                             dy = 0.5*a_out[1] + Q('0.5cm'),
                                             dz = 0.5*globals.get("ArapucaIn_z"))
        arapucaDoubleWallsBox = geom.shapes.Boolean('ArapucaDoubleWalls',
                                                    type = 'subtraction',
                                                    first = arapucaOutBox,
                                                    second = arapucaDoubleInBox,
                                                    pos = geom.structure.Position('posArapucaDoubleSub',
                                                                                  x = Q('0cm'),
                                                                                  y = Q('0cm'),
                                                                                  z = Q('0cm'))
                                                    )
        arapucaDoubleAccBox = geom.shapes.Box('ArapucaDoubleAcceptanceWindow',
                                              dx = 0.5*a_acc[0],
                                              dy = 0.5*a_out[1] - Q('0.01cm'),
                                              dz = 0.5*a_acc[2])

        # define all the sub-volumes
        opdetsens_LV = geom.structure.Volume('volOpDetSensitive',
                                             material = "LAr",
                                             shape = arapucaAccBox)
        arapuca_LV = geom.structure.Volume('Arapuca',
                                           material = "G10",
                                           shape = arapucaWallsBox)
        # define the larger volumes
        arapucaenc_LV = geom.structure.Volume('volArapuca',
                                              material = "LAr",
                                              shape = arapucaEnclosureBox)
        # add it to the builder
        self.add_volume(arapucaenc_LV)

        # now do the placements for each
        arapucaenc_LV     = self.placeArapuca(geom, arapucaenc_LV, arapuca_LV, opdetsens_LV,
                                              opdet_pos = geom.structure.Position('opdetshift',
                                                                                  x = Q('0cm'),
                                                                                  y = 0.5*a_acc[1],
                                                                                  z = Q('0cm')))
        # Deal with double-sided cathode arapucas, for the case of 2 drift volumes
        if globals.get("nCRM_x") == 2:
            # define all the sub-volumes
            opdetsens2_LV = geom.structure.Volume('volOpDetSensitiveDouble',
                                                 material = "LAr",
                                                 shape = arapucaDoubleAccBox)
            arapuca2_LV = geom.structure.Volume('ArapucaDouble',
                                                material = "G10",
                                                shape = arapucaDoubleWallsBox)
            # define the larger volumes
            arapucaenc2_LV = geom.structure.Volume('volArapucaDouble',
                                                   material = "LAr",
                                                   shape = arapucaEnclosureBox)
            # add it to the builder
            self.add_volume(arapucaenc2_LV)

            # now do the placements for each
            arapucaenc2_LV     = self.placeArapuca(geom, arapucaenc2_LV, arapuca2_LV, opdetsens2_LV,
                                                   opdet_pos="posCenter")

        # opt-in: build the X-Arapuca mesh volumes (placements happen in Cryostat)
        if globals.get("ArapucaMesh_switch"):
            self.constructMembraneMesh(geom)
            self.constructCathodeArapucaMesh(geom)
            self.constructResistiveCathodeMesh(geom)
        return

    # helper for arapuca placements
    def placeArapuca(self, geom, arapucaenc_LV, arapuca_LV, opdet_LV, opdet_pos, rotArapuca="rIdentity"):
        place1 = geom.structure.Placement('placearapuca_in'+arapucaenc_LV.name,
                                          volume = arapuca_LV,
                                          pos = "posCenter",
                                          rot = rotArapuca
                                          )
        place2 = geom.structure.Placement('placeopdet_in'+arapucaenc_LV.name,
                                          volume = opdet_LV,
                                          pos = opdet_pos,
                                          )
        arapucaenc_LV.placements.append(place1.name)
        arapucaenc_LV.placements.append(place2.name)
        return arapucaenc_LV

    # build the membrane lateral X-Arapuca mesh: steel frame (7-step Boolean union)
    # + inner rod array, all inside an LAr module box. Mirrors perl gen_ArapucaMesh.
    def constructMembraneMesh(self, geom):
        tube_len_v = globals.get("ArapucaMeshTubeLength_vertical")
        tube_len_h = globals.get("ArapucaMeshTubeLength_horizontal")
        rmin = globals.get("ArapucaMeshInnerRadious")
        rmax = globals.get("ArapucaMeshOuterRadious")
        tor_rad = globals.get("ArapucaMeshTorRad")
        inner_len_v = globals.get("ArapucaMeshInnerStructureLength_vertical")
        inner_len_h = globals.get("ArapucaMeshInnerStructureLength_horizontal")
        rod_rmin = globals.get("ArapucaMeshRodInnerRadious")
        rod_rmax = globals.get("ArapucaMeshRodOuterRadious")
        inner_sep = globals.get("ArapucaMeshInnerStructureSeparation")
        n_v = globals.get("ArapucaMeshInnerStructureNumberOfBars_vertical")
        n_h = globals.get("ArapucaMeshInnerStructureNumberOfBars_horizontal")

        # base shapes
        corner = geom.shapes.Torus('ArapucaMeshCorner',
                                   rmin = rmin, rmax = rmax, rtor = tor_rad,
                                   startphi = Q('0deg'), deltaphi = Q('90deg'))
        tube_v = geom.shapes.Tubs('ArapucaMeshtube_vertical',
                                  rmin = rmin, rmax = rmax,
                                  dz = 0.5*tube_len_v,
                                  sphi = Q('0deg'), dphi = Q('360deg'))
        tube_h = geom.shapes.Tubs('ArapucaMeshtube_horizontal',
                                  rmin = rmin, rmax = rmax,
                                  dz = 0.5*tube_len_h,
                                  sphi = Q('0deg'), dphi = Q('360deg'))
        # dz shrunk from perl's `+ 2*tor_rad` padding to `+ 2*1cm`: the wider perl box was
        # extending into adjacent meshes and into the gaseous-argon layer at the cryostat top.
        # See protodunevd/xarapuca.py construct_membrane_mesh for the original observation.
        module = geom.shapes.Box('ArapucaMeshModule',
                                 dx = 0.5*(inner_len_h + 2*(rmax + tor_rad)),
                                 dy = 0.5*(2*rod_rmax + Q('1cm')),
                                 dz = 0.5*(inner_len_v + 2*(rmax + Q('1cm'))))
        rod_v = geom.shapes.Tubs('ArapucaMeshRod_vertical',
                                 rmin = rod_rmin, rmax = rod_rmax,
                                 dz = 0.5*inner_len_v,
                                 sphi = Q('0deg'), dphi = Q('360deg'))
        rod_h = geom.shapes.Tubs('ArapucaMeshRod_horizontal',
                                 rmin = rod_rmin, rmax = rod_rmax,
                                 dz = 0.5*inner_len_h,
                                 sphi = Q('0deg'), dphi = Q('360deg'))

        # 7-step Boolean union for the steel frame (Meshunion1..7); rotation
        # sequence matches the FieldShaper construction in FieldCage.py
        xz_positions = [(-tor_rad,                  0.5*tube_len_v),
                        (-0.5*tube_len_h - tor_rad, 0.5*tube_len_v + tor_rad),
                        (-tube_len_h - tor_rad,     0.5*tube_len_v),
                        (-tube_len_h - 2*tor_rad,   Q('0cm')),
                        (-tube_len_h - tor_rad,     -0.5*tube_len_v),
                        (-0.5*tube_len_h - tor_rad, -0.5*tube_len_v - tor_rad),
                        (-tor_rad,                  -0.5*tube_len_v)]
        rotations = ['rPlus90AboutX',
                     'rPlus90AboutY',
                     'rPlus90AboutXMinux90AboutY',
                     'rIdentity',
                     'rPlus90AboutXPlus180AboutY',
                     'rPlus90AboutY',
                     'rPlus90AboutXPlus90AboutY']
        pos_names = ['Meshcorner1', 'Meshside2', 'Meshcorner2', 'Meshside3',
                     'Meshcorner3', 'Meshside4', 'Meshcorner4']

        unionShape = tube_v
        for ui in range(1, 8):
            if ui % 2 == 1:
                secondShape = corner
            elif ui % 4 == 0:
                secondShape = tube_v
            else:
                secondShape = tube_h
            unionShape = geom.shapes.Boolean('Meshunion'+str(ui),
                                             type = 'union',
                                             first = unionShape,
                                             second = secondShape,
                                             pos = geom.structure.Position(pos_names[ui-1],
                                                                           x = xz_positions[ui-1][0],
                                                                           y = Q('0cm'),
                                                                           z = xz_positions[ui-1][1]),
                                             rot = rotations[ui-1])

        frame_LV = geom.structure.Volume('volMeshunion',
                                         material = 'STEEL_STAINLESS_Fe7Cr2Ni',
                                         shape = unionShape)
        rod_v_LV = geom.structure.Volume('volArapucaMeshRod_vertical',
                                         material = 'STEEL_STAINLESS_Fe7Cr2Ni',
                                         shape = rod_v)
        rod_h_LV = geom.structure.Volume('volArapucaMeshRod_horizontal',
                                         material = 'STEEL_STAINLESS_Fe7Cr2Ni',
                                         shape = rod_h)
        mesh_LV = geom.structure.Volume('volArapucaMesh',
                                        material = 'LAr',
                                        shape = module)

        # place frame inside the module
        frame_pos = geom.structure.Position('posMesh18',
                                            x = 0.5*tube_len_h + tor_rad,
                                            y = Q('0cm'),
                                            z = Q('0cm'))
        frame_place = geom.structure.Placement('placeMeshunion_inArapucaMesh',
                                               volume = frame_LV,
                                               pos = frame_pos)
        mesh_LV.placements.append(frame_place.name)

        # place inner rods (vertical and horizontal)
        for ii in range(n_v):
            pos = geom.structure.Position('posMeshRod_vertical'+str(ii),
                                          x = -5*inner_sep + ii*inner_sep,
                                          y = Q('0.00001cm') + 2*rod_rmax,
                                          z = Q('0cm'))
            place = geom.structure.Placement('placeArapucaMeshRod_vertical'+str(ii),
                                             volume = rod_v_LV, pos = pos)
            mesh_LV.placements.append(place.name)
        for ii in range(n_h):
            pos = geom.structure.Position('posMeshRod_horizontal1'+str(ii),
                                          x = Q('0cm'), y = Q('0cm'),
                                          z = -4*inner_sep + ii*inner_sep)
            place = geom.structure.Placement('placeArapucaMeshRod_horizontal'+str(ii),
                                             volume = rod_h_LV, pos = pos,
                                             rot = 'rPlus90AboutY')
            mesh_LV.placements.append(place.name)

        self.add_volume(mesh_LV)
        return mesh_LV

    # build the cathode-side conductive mesh: thin steel rod grid inside an LAr
    # module that gets placed flush against both faces of each cathode arapuca.
    def constructCathodeArapucaMesh(self, geom):
        rod_r = globals.get("CathodeArapucaMeshRodRadious")
        rod_sep = globals.get("CathodeArapucaMeshRodSeparation")
        off_v = globals.get("CathodeArapucaMesh_verticalOffset")
        off_h = globals.get("CathodeArapucaMesh_horizontalOffset")
        cath_void_len = globals.get("lengthCathodeVoid")
        cath_void_wid = globals.get("widthCathodeVoid")
        n_vert = int(globals.get("CathodeArapucaMeshNumberOfBars_vertical").magnitude)
        n_horiz = int(globals.get("CathodeArapucaMeshNumberOfBars_horizontal").magnitude)

        module = geom.shapes.Box('CathodeArapucaMeshModule',
                                 dx = 0.5*(4*rod_r + Q('1e-9cm')),
                                 dy = 0.5*cath_void_len,
                                 dz = 0.5*cath_void_wid)
        rod_v = geom.shapes.Tubs('CathodeArapucaMeshRod_vertical',
                                 rmin = Q('0cm'), rmax = rod_r,
                                 dz = 0.5*cath_void_wid,
                                 sphi = Q('0deg'), dphi = Q('360deg'))
        rod_h = geom.shapes.Tubs('CathodeArapucaMeshRod_horizontal',
                                 rmin = Q('0cm'), rmax = rod_r,
                                 dz = 0.5*cath_void_len,
                                 sphi = Q('0deg'), dphi = Q('360deg'))

        rod_v_LV = geom.structure.Volume('volCathodeArapucaMeshRod_vertical',
                                         material = 'STEEL_STAINLESS_Fe7Cr2Ni',
                                         shape = rod_v)
        rod_h_LV = geom.structure.Volume('volCathodeArapucaMeshRod_horizontal',
                                         material = 'STEEL_STAINLESS_Fe7Cr2Ni',
                                         shape = rod_h)
        mesh_LV = geom.structure.Volume('volCathodeArapucaMesh',
                                        material = 'LAr',
                                        shape = module)

        for ii in range(n_vert):
            pos = geom.structure.Position('posCathodeMeshRod_vertical'+str(ii),
                                          x = -(rod_r + Q('1e-9cm')/2),
                                          y = -0.5*cath_void_len + off_v + ii*rod_sep,
                                          z = Q('0cm'))
            place = geom.structure.Placement('placeCathodeMeshRod_vertical'+str(ii),
                                             volume = rod_v_LV, pos = pos)
            mesh_LV.placements.append(place.name)
        for ii in range(n_horiz):
            pos = geom.structure.Position('posMeshRod_horizontal2'+str(ii),
                                          x = (rod_r + Q('1e-9cm')/2),
                                          y = Q('0cm'),
                                          z = -0.5*cath_void_wid + off_h + ii*rod_sep)
            place = geom.structure.Placement('placeCathodeMeshRod_horizontal'+str(ii),
                                             volume = rod_h_LV, pos = pos,
                                             rot = 'rPlus90AboutX')
            mesh_LV.placements.append(place.name)

        self.add_volume(mesh_LV)
        return mesh_LV

    # build the cathode resistive mesh: iterative Boolean union of G10 strips.
    # The volume volCathodeMeshunion is what gets placed on the cathode in Cryostat;
    # the perl wrapper volCathodeMesh is unused and not built.
    def constructResistiveCathodeMesh(self, geom):
        sep = globals.get("CathodeMeshInnerStructureSeparation")
        width = globals.get("CathodeMeshInnerStructureWidth")
        thick = globals.get("CathodeMeshInnerStructureThickness")
        len_v = globals.get("CathodeMeshInnerStructureLength_vertical")
        len_h = globals.get("CathodeMeshInnerStructureLength_horizontal")
        n_vert = globals.get("CathodeMeshInnerStructureNumberOfStrips_vertical")
        n_horiz = globals.get("CathodeMeshInnerStructureNumberOfStrips_horizontal")

        strip_v = geom.shapes.Box('CathodeMeshStrip_vertical',
                                  dx = 0.5*thick, dy = 0.5*width, dz = 0.5*len_v)
        strip_h = geom.shapes.Box('CathodeMeshStrip_horizontal',
                                  dx = 0.5*thick, dy = 0.5*len_h, dz = 0.5*width)

        meshShape = geom.shapes.Boolean('CathodeMeshunion1',
                                        type = 'union',
                                        first = strip_v, second = strip_v,
                                        pos = geom.structure.Position('posMeshStrip_vertical1',
                                                                      x = Q('0cm'),
                                                                      y = sep,
                                                                      z = Q('0cm')))
        for ii in range(2, n_vert):
            meshShape = geom.shapes.Boolean('CathodeMeshunion'+str(ii),
                                            type = 'union',
                                            first = meshShape, second = strip_v,
                                            pos = geom.structure.Position('posMeshStrip_vertical'+str(ii),
                                                                          x = Q('0cm'),
                                                                          y = ii*sep,
                                                                          z = Q('0cm')))

        # post-vertical-loop $ii in perl equals n_vert; first horizontal union uses that
        ii = n_vert
        # center horizontal strips on the vertical-strip cluster center in y, and center the
        # cluster of horizontal strips at z=0 in local. Perl's formulas only collapse to these
        # values when wcv == (n_vert+1)*sep - width (protodune-specific).
        horiz_y = 0.5*(n_vert - 1)*sep
        horiz_z = -0.5*(n_horiz - 1)*sep
        meshShape = geom.shapes.Boolean('CathodeMeshunion'+str(ii),
                                        type = 'union',
                                        first = meshShape, second = strip_h,
                                        pos = geom.structure.Position('posMeshStrip_horizontal0',
                                                                      x = Q('0cm'),
                                                                      y = horiz_y,
                                                                      z = horiz_z))
        for jj in range(1, n_horiz):
            meshShape = geom.shapes.Boolean('CathodeMeshunion'+str(ii+jj),
                                            type = 'union',
                                            first = meshShape, second = strip_h,
                                            pos = geom.structure.Position('posMeshStrip_horizontal'+str(jj),
                                                                          x = Q('0cm'),
                                                                          y = horiz_y,
                                                                          z = horiz_z + jj*sep))

        union_LV = geom.structure.Volume('volCathodeMeshunion',
                                         material = 'G10',
                                         shape = meshShape)
        self.add_volume(union_LV)
        return union_LV
