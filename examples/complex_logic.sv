// Complex logic example
// Demonstrates multiple gate types: AND, OR, NAND, NOR, XOR, XNOR, NOT, BUF

module complex_logic(a, b, c, d, y1, y2, y3, y4, y5, y6);
  input logic a, b, c, d;
  output logic y1, y2, y3, y4, y5, y6;

  logic a_buf, b_not, ab_and, cd_or, ab_nand, cd_nor, ac_xor, bd_xnor;

  // Buffer and inverter
  BUF u1(a, a_buf);
  NOT u2(b, b_not);

  // Basic gates
  AND u3(a, b, ab_and);
  OR u4(c, d, cd_or);

  // NAND and NOR gates
  NAND u5(a, b, ab_nand);
  NOR u6(c, d, cd_nor);

  // XOR and XNOR gates
  XOR u7(a, c, ac_xor);
  XNOR u8(b, d, bd_xnor);

  // Complex combinations
  AND u9(a_buf, b_not, y1);
  OR u10(ab_and, cd_or, y2);
  XOR u11(ab_nand, cd_nor, y3);
  NAND u12(ac_xor, bd_xnor, y4);
  NOR u13(y1, y2, y5);
  XNOR u14(y3, y4, y6);
endmodule