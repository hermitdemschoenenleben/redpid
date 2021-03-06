csr_constants = {
    'control_loop_iir_a_shift': 16,
    'control_loop_iir_a_width': 18,
    'control_loop_iir_a_interval': 1,
    'control_loop_iir_a_latency': 2,
    'control_loop_iir_a_order': 1,
    'control_loop_iir_a_iterative': 0,
    'control_loop_iir_b_shift': 23,
    'control_loop_iir_b_width': 25,
    'control_loop_iir_b_interval': 5,
    'control_loop_iir_b_latency': 6,
    'control_loop_iir_b_order': 2,
    'control_loop_iir_b_iterative': 1,
    'control_loop_iir_c_shift': 16,
    'control_loop_iir_c_width': 18,
    'control_loop_iir_c_interval': 1,
    'control_loop_iir_c_latency': 2,
    'control_loop_iir_c_order': 1,
    'control_loop_iir_c_iterative': 0,
    'control_loop_iir_d_shift': 16,
    'control_loop_iir_d_width': 18,
    'control_loop_iir_d_interval': 1,
    'control_loop_iir_d_latency': 3,
    'control_loop_iir_d_order': 2,
    'control_loop_iir_d_iterative': 0,
    'control_loop_iir_e_shift': 23,
    'control_loop_iir_e_width': 25,
    'control_loop_iir_e_interval': 5,
    'control_loop_iir_e_latency': 6,
    'control_loop_iir_e_order': 2,
    'control_loop_iir_e_iterative': 1,
}

csr = {
    'control_loop_x_tap': (0, 0x000, 2, True),
    'control_loop_brk': (0, 0x001, 1, True),
    'control_loop_y_tap': (0, 0x002, 2, True),
    'control_loop_pid_setpoint': (0, 0x003, 14, True),
    'control_loop_pid_kp': (0, 0x005, 14, True),
    'control_loop_pid_ki': (0, 0x007, 14, True),
    'control_loop_pid_reset': (0, 0x009, 1, True),
    'control_loop_pid_kd': (0, 0x00a, 14, True),
    'control_loop_iir_a_z0': (0, 0x00c, 27, True),
    'control_loop_iir_a_a1': (0, 0x010, 18, True),
    'control_loop_iir_a_b0': (0, 0x013, 18, True),
    'control_loop_iir_a_b1': (0, 0x016, 18, True),
    'control_loop_iir_b_z0': (0, 0x019, 38, True),
    'control_loop_iir_b_a1': (0, 0x01e, 25, True),
    'control_loop_iir_b_a2': (0, 0x022, 25, True),
    'control_loop_iir_b_b0': (0, 0x026, 25, True),
    'control_loop_iir_b_b1': (0, 0x02a, 25, True),
    'control_loop_iir_b_b2': (0, 0x02e, 25, True),
    'control_loop_x_limit_min': (0, 0x032, 25, True),
    'control_loop_x_limit_max': (0, 0x036, 25, True),
    'control_loop_iir_c_z0': (0, 0x03a, 27, True),
    'control_loop_iir_c_a1': (0, 0x03e, 18, True),
    'control_loop_iir_c_b0': (0, 0x041, 18, True),
    'control_loop_iir_c_b1': (0, 0x044, 18, True),
    'control_loop_iir_d_z0': (0, 0x047, 27, True),
    'control_loop_iir_d_a1': (0, 0x04b, 18, True),
    'control_loop_iir_d_a2': (0, 0x04e, 18, True),
    'control_loop_iir_d_b0': (0, 0x051, 18, True),
    'control_loop_iir_d_b1': (0, 0x054, 18, True),
    'control_loop_iir_d_b2': (0, 0x057, 18, True),
    'control_loop_iir_e_z0': (0, 0x05a, 38, True),
    'control_loop_iir_e_a1': (0, 0x05f, 25, True),
    'control_loop_iir_e_a2': (0, 0x063, 25, True),
    'control_loop_iir_e_b0': (0, 0x067, 25, True),
    'control_loop_iir_e_b1': (0, 0x06b, 25, True),
    'control_loop_iir_e_b2': (0, 0x06f, 25, True),
    'control_loop_y_limit_min': (0, 0x073, 14, True),
    'control_loop_y_limit_max': (0, 0x075, 14, True),
    'control_loop_decimation': (0, 0x077, 10, True),
    'control_loop_sequence_player_enabled': (0, 0x079, 1, True),
    'control_loop_sequence_player_run_algorithm': (0, 0x07a, 1, True),
    'control_loop_sequence_player_stop_algorithm_after': (0, 0x07b, 30, True),
    'control_loop_sequence_player_start_clocks': (0, 0x07f, 1, True),
    'control_loop_sequence_player_max_state': (0, 0x080, 10, True),
    'control_loop_sequence_player_last_point': (0, 0x082, 14, True),
    'control_loop_sequence_player_request_stop': (0, 0x084, 1, True),
    'control_loop_sequence_player_stop_after': (0, 0x085, 30, True),
    'control_loop_sequence_player_stop_zone': (0, 0x089, 3, True),
    'control_loop_sequence_player_request_recording': (0, 0x08a, 1, True),
    'control_loop_sequence_player_record_after': (0, 0x08b, 30, True),
    'control_loop_sequence_player_data_out': (0, 0x08f, 14, False),
    'control_loop_sequence_player_data_out_addr': (0, 0x091, 14, True),
    'control_loop_sequence_player_error_signal_out': (0, 0x093, 2, False),
    'control_loop_sequence_player_error_signal_out_addr': (0, 0x094, 14, True),
    'control_loop_sequence_player_data_in': (0, 0x096, 14, True),
    'control_loop_sequence_player_data_addr': (0, 0x098, 14, True),
    'control_loop_sequence_player_data_write': (0, 0x09a, 1, True),
    'control_loop_sequence_player_step_size': (0, 0x09b, 14, True),
    'control_loop_sequence_player_decrease_step_size_after': (0, 0x09d, 16, True),
    'control_loop_sequence_player_keep_constant_at_end': (0, 0x09f, 14, True),
    'control_loop_sequence_player_zone_edge_0': (0, 0x0a1, 15, True),
    'control_loop_sequence_player_zone_edge_1': (0, 0x0a3, 15, True),
    'control_loop_sequence_player_zone_edge_2': (0, 0x0a5, 15, True),
    'control_loop_sequence_player_ff_direction_0': (0, 0x0a7, 2, True),
    'control_loop_sequence_player_ff_direction_1': (0, 0x0a8, 2, True),
    'control_loop_sequence_player_ff_direction_2': (0, 0x0a9, 2, True),
    'control_loop_sequence_player_ff_direction_3': (0, 0x0aa, 2, True),
    'control_loop_sequence_player_ff_curvature_0': (0, 0x0ab, 2, True),
    'control_loop_sequence_player_ff_curvature_filtering_start_0': (0, 0x0ac, 14, True),
    'control_loop_sequence_player_ff_curvature_1': (0, 0x0ae, 2, True),
    'control_loop_sequence_player_ff_curvature_filtering_start_1': (0, 0x0af, 14, True),
    'control_loop_sequence_player_ff_curvature_2': (0, 0x0b1, 2, True),
    'control_loop_sequence_player_ff_curvature_filtering_start_2': (0, 0x0b2, 14, True),
    'control_loop_sequence_player_ff_curvature_3': (0, 0x0b4, 2, True),
    'control_loop_sequence_player_ff_curvature_filtering_start_3': (0, 0x0b5, 14, True),
    'control_loop_x_clr': (0, 0x0b7, 1, True),
    'control_loop_x_max': (0, 0x0b8, 25, False),
    'control_loop_x_min': (0, 0x0bc, 25, False),
    'control_loop_y_clr': (0, 0x0c0, 1, True),
    'control_loop_y_max': (0, 0x0c1, 25, False),
    'control_loop_y_min': (0, 0x0c5, 25, False),
    'control_loop_other_x_clr': (0, 0x0c9, 1, True),
    'control_loop_other_x_max': (0, 0x0ca, 25, False),
    'control_loop_other_x_min': (0, 0x0ce, 25, False),
    'control_loop_pid_out_clr': (0, 0x0d2, 1, True),
    'control_loop_pid_out_max': (0, 0x0d3, 25, False),
    'control_loop_pid_out_min': (0, 0x0d7, 25, False),
    'control_loop_x_hold_en': (0, 0x0db, 37, True),
    'control_loop_x_clear_en': (0, 0x0e0, 37, True),
    'control_loop_y_hold_en': (0, 0x0e5, 37, True),
    'control_loop_y_clear_en': (0, 0x0ea, 37, True),
    'control_loop_pid_enable_en': (0, 0x0ef, 37, True),
    'control_loop_dx_sel': (0, 0x0f4, 3, True),
    'control_loop_dy_sel': (0, 0x0f5, 3, True),
    'control_loop_rx_sel': (0, 0x0f6, 3, True),
    'dna_dna': (28, 0x000, 64, False),
    'gpio_n_ins': (30, 0x000, 8, False),
    'gpio_n_outs': (30, 0x001, 8, True),
    'gpio_n_oes': (30, 0x002, 8, True),
    'gpio_n_state': (30, 0x003, 37, False),
    'gpio_n_state_clr': (30, 0x008, 1, True),
    'gpio_n_do0_en': (30, 0x009, 37, True),
    'gpio_n_do1_en': (30, 0x00e, 37, True),
    'gpio_n_do2_en': (30, 0x013, 37, True),
    'gpio_n_do3_en': (30, 0x018, 37, True),
    'gpio_n_do4_en': (30, 0x01d, 37, True),
    'gpio_n_do5_en': (30, 0x022, 37, True),
    'gpio_n_do6_en': (30, 0x027, 37, True),
    'gpio_n_do7_en': (30, 0x02c, 37, True),
    'gpio_p_ins': (31, 0x000, 8, False),
    'gpio_p_outs': (31, 0x001, 8, True),
    'gpio_p_oes': (31, 0x002, 8, True),
    'ttl_ttl0_start': (1, 0x000, 40, True),
    'ttl_ttl0_end': (1, 0x005, 40, True),
    'ttl_ttl1_start': (1, 0x00a, 40, True),
    'ttl_ttl1_end': (1, 0x00f, 40, True),
    'ttl_ttl2_start': (1, 0x014, 40, True),
    'ttl_ttl2_end': (1, 0x019, 40, True),
    'ttl_ttl3_start': (1, 0x01e, 40, True),
    'ttl_ttl3_end': (1, 0x023, 40, True),
    'ttl_ttl4_start': (1, 0x028, 40, True),
    'ttl_ttl4_end': (1, 0x02d, 40, True),
    'ttl_ttl5_start': (1, 0x032, 40, True),
    'ttl_ttl5_end': (1, 0x037, 40, True),
    'ttl_ttl6_start': (1, 0x03c, 40, True),
    'ttl_ttl6_end': (1, 0x041, 40, True),
    'ttl_ttl7_start': (1, 0x046, 40, True),
    'ttl_ttl7_end': (1, 0x04b, 40, True),
    'ttl_ttl8_start': (1, 0x050, 40, True),
    'ttl_ttl8_end': (1, 0x055, 40, True),
    'ttl_ttl9_start': (1, 0x05a, 40, True),
    'ttl_ttl9_end': (1, 0x05f, 40, True),
    'ttl_ttl10_start': (1, 0x064, 40, True),
    'ttl_ttl10_end': (1, 0x069, 40, True),
    'ttl_ttl11_start': (1, 0x06e, 40, True),
    'ttl_ttl11_end': (1, 0x073, 40, True),
    'ttl_ttl12_start': (1, 0x078, 40, True),
    'ttl_ttl12_end': (1, 0x07d, 40, True),
    'ttl_ttl13_start': (1, 0x082, 40, True),
    'ttl_ttl13_end': (1, 0x087, 40, True),
    'ttl_ttl14_start': (1, 0x08c, 40, True),
    'ttl_ttl14_end': (1, 0x091, 40, True),
    'ttl_ttl15_start': (1, 0x096, 40, True),
    'ttl_ttl15_end': (1, 0x09b, 40, True),
    'ttl_ttl16_start': (1, 0x0a0, 40, True),
    'ttl_ttl16_end': (1, 0x0a5, 40, True),
    'ttl_ttl17_start': (1, 0x0aa, 40, True),
    'ttl_ttl17_end': (1, 0x0af, 40, True),
    'ttl_ttl18_start': (1, 0x0b4, 40, True),
    'ttl_ttl18_end': (1, 0x0b9, 40, True),
    'ttl_ttl19_start': (1, 0x0be, 40, True),
    'ttl_ttl19_end': (1, 0x0c3, 40, True),
    'xadc_temp': (29, 0x000, 12, False),
    'xadc_v': (29, 0x002, 12, False),
    'xadc_a': (29, 0x004, 12, False),
    'xadc_b': (29, 0x006, 12, False),
    'xadc_c': (29, 0x008, 12, False),
    'xadc_d': (29, 0x00a, 12, False),
}
states = ['force', 'di0', 'di1', 'di2', 'di3', 'di4', 'di5', 'di6', 'di7', 'control_loop_x_sat', 'control_loop_x_railed', 'control_loop_y_sat', 'control_loop_y_railed', 'control_loop_clock_0', 'control_loop_clock_1', 'control_loop_clock_2', 'control_loop_clock_3', 'ttl_ttl0_out', 'ttl_ttl1_out', 'ttl_ttl2_out', 'ttl_ttl3_out', 'ttl_ttl4_out', 'ttl_ttl5_out', 'ttl_ttl6_out', 'ttl_ttl7_out', 'ttl_ttl8_out', 'ttl_ttl9_out', 'ttl_ttl10_out', 'ttl_ttl11_out', 'ttl_ttl12_out', 'ttl_ttl13_out', 'ttl_ttl14_out', 'ttl_ttl15_out', 'ttl_ttl16_out', 'ttl_ttl17_out', 'ttl_ttl18_out', 'ttl_ttl19_out']
signals = ['zero', 'control_loop_x', 'control_loop_y', 'control_loop_other_x', 'control_loop_pid_out']
