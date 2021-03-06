#
# Copyright (c) 2020, RTE (http://www.rte-france.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import unittest
import gridpy.network
import gridpy.loadflow
import gridpy.security_analysis
import gridpy.sensitivity_analysis
import gridpy as gp


class GridPyTestCase(unittest.TestCase):
    @staticmethod
    def test_print_version():
        gp.print_version()

    def test_create_empty_network(self):
        n = gp.network.create_empty("test")
        self.assertIsNotNone(n)

    def test_run_lf(self):
        n = gp.network.create_ieee14()
        results = gp.loadflow.run_ac(n)
        self.assertEqual(1, len(results))
        self.assertEqual(gp.loadflow.ComponentStatus.CONVERGED, list(results)[0].status)
        parameters = gp.loadflow.Parameters(distributed_slack=False)
        results = gp.loadflow.run_dc(n, parameters)
        self.assertEqual(1, len(results))

    def test_load_network(self):
        dir = os.path.dirname(os.path.realpath(__file__))
        n = gp.network.load(dir + "/empty-network.xml")
        self.assertIsNotNone(n)

    def test_buses(self):
        n = gp.network.create_ieee14()
        self.assertEqual(14, len(n.buses))
        b = list(n.buses)[0]
        self.assertEqual('VL1_0', b.id)
        self.assertEqual(1.06, b.v_magnitude)
        self.assertEqual(0.0, b.v_angle)
        self.assertEqual(0, b.component_num)

    def test_generators(self):
        n = gp.network.create_ieee14()
        self.assertEqual(5, len(n.generators))
        g = list(n.generators)[0]
        self.assertEqual('B1-G', g.id)
        self.assertEqual(232.4, g.target_p)
        self.assertEqual(-9999.0, g.min_p)
        self.assertEqual(9999.0, g.max_p)
        self.assertEqual(1.0, g.nominal_voltage)
        self.assertIsNone(g.country)
        self.assertIsNotNone(g.bus)
        self.assertEqual('VL1_0', g.bus.id)

    def test_loads(self):
        n = gp.network.create_ieee14()
        self.assertEqual(11, len(n.loads))
        l = list(n.loads)[0]
        self.assertEqual('B2-L', l.id)
        self.assertEqual(21.7, l.p0)
        self.assertEqual(1.0, l.nominal_voltage)
        self.assertIsNone(l.country)
        self.assertIsNotNone(l.bus)
        self.assertEqual('VL2_0', l.bus.id)

    def test_connect_disconnect(self):
        n = gp.network.create_ieee14()
        self.assertTrue(n.disconnect('L1-2-1'))
        self.assertTrue(n.connect('L1-2-1'))

    def test_security_analysis(self):
        n = gp.network.create_eurostag_tutorial_example1_network()
        sa = gp.security_analysis.create()
        sa.add_single_element_contingency('NHV1_NHV2_1', 'First contingency')
        sa_result = sa.run_ac(n)
        self.assertEqual(1, len(sa_result._post_contingency_results))

    def test_get_network_element_ids(self):
        n = gp.network.create_eurostag_tutorial_example1_network()
        self.assertEqual(['NGEN_NHV1', 'NHV2_NLOAD'], n.get_elements_ids(gp.network.ElementType.TWO_WINDINGS_TRANSFORMER))
        self.assertEqual(['NGEN_NHV1'], n.get_elements_ids(element_type=gp.network.ElementType.TWO_WINDINGS_TRANSFORMER, nominal_voltages={24}))
        self.assertEqual(['NGEN_NHV1', 'NHV2_NLOAD'], n.get_elements_ids(element_type=gp.network.ElementType.TWO_WINDINGS_TRANSFORMER, nominal_voltages={24, 150}))
        self.assertEqual(['LOAD'], n.get_elements_ids(element_type=gp.network.ElementType.LOAD, nominal_voltages={150}))
        self.assertEqual(['LOAD'], n.get_elements_ids(element_type=gp.network.ElementType.LOAD, nominal_voltages={150}, countries={'FR'}))
        self.assertEqual([], n.get_elements_ids(element_type=gp.network.ElementType.LOAD, nominal_voltages={150}, countries={'BE'}))
        self.assertEqual(['NGEN_NHV1'], n.get_elements_ids(element_type=gp.network.ElementType.TWO_WINDINGS_TRANSFORMER, nominal_voltages={24}, countries={'FR'}))
        self.assertEqual([], n.get_elements_ids(element_type=gp.network.ElementType.TWO_WINDINGS_TRANSFORMER, nominal_voltages={24}, countries={'BE'}))

    def test_create_generators_data_frame(self):
        n = gp.network.create_eurostag_tutorial_example1_network()
        df = n.create_generators_data_frame()
        self.assertEqual('OTHER', df['energy_source']['GEN'])
        self.assertEqual(607, df['target_p']['GEN'])

    def test_sensitivity_analysis(self):
        n = gp.network.create_ieee14()
        sa = gp.sensitivity_analysis.create()
        sa.add_single_element_contingency('L1-2-1')
        sa.set_factor_matrix(['L1-5-1', 'L2-3-1'], ['B1-G', 'B2-G', 'B3-G'])
        r = sa.run_dc(n)

        df = r.get_sensitivity_matrix()
        self.assertEqual((3, 2), df.shape)
        self.assertEqual(0.08099067519128486, df['L1-5-1']['B1-G'])
        self.assertEqual(-0.08099067519128486, df['L1-5-1']['B2-G'])
        self.assertEqual(-0.17249763831611517, df['L1-5-1']['B3-G'])
        self.assertEqual(-0.013674968450008108, df['L2-3-1']['B1-G'])
        self.assertEqual(0.013674968450008108, df['L2-3-1']['B2-G'])
        self.assertEqual(-0.5456827116267954, df['L2-3-1']['B3-G'])

        df = r.get_reference_flows()
        self.assertEqual((1, 2), df.shape)
        self.assertAlmostEqual(72.24667948865367, df['L1-5-1']['reference_flows'], places=6)
        self.assertAlmostEqual(69.83139138110104, df['L2-3-1']['reference_flows'], places=6)

        df = r.get_post_contingency_sensitivity_matrix('L1-2-1')
        self.assertEqual((3, 2), df.shape)
        self.assertEqual(0.49999999999999994, df['L1-5-1']['B1-G'])
        self.assertEqual(-0.49999999999999994, df['L1-5-1']['B2-G'])
        self.assertEqual(-0.49999999999999994, df['L1-5-1']['B3-G'])
        self.assertEqual(-0.08442310437411704, df['L2-3-1']['B1-G'])
        self.assertEqual(0.08442310437411704, df['L2-3-1']['B2-G'])
        self.assertEqual(-0.49038517950037847, df['L2-3-1']['B3-G'])

        df = r.get_post_contingency_reference_flows('L1-2-1')
        self.assertEqual((1, 2), df.shape)
        self.assertAlmostEqual(225.69999999999996, df['L1-5-1']['reference_flows'], places=6)
        self.assertAlmostEqual(43.92137999293259, df['L2-3-1']['reference_flows'], places=6)

        self.assertIsNone(r.get_post_contingency_sensitivity_matrix('aaa'))

    def test_exception(self):
        n = gp.network.create_ieee14()
        try:
            n.open_switch("aa")
            self.fail()
        except gp.GridPyError as e:
            self.assertEqual("Switch 'aa' not found", str(e))


if __name__ == '__main__':
    unittest.main()
