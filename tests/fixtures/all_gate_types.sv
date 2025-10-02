// Test all supported gate types
module all_gate_types(a, b, y_and, y_or, y_nand, y_nor, y_xor, y_xnor, y_not, y_buf);
  input logic a, b;
  output logic y_and, y_or, y_nand, y_nor, y_xor, y_xnor, y_not, y_buf;

  AND u1(a, b, y_and);
  OR u2(a, b, y_or);
  NAND u3(a, b, y_nand);
  NOR u4(a, b, y_nor);
  XOR u5(a, b, y_xor);
  XNOR u6(a, b, y_xnor);
  NOT u7(a, y_not);
  BUF u8(a, y_buf);
endmodule
