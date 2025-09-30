// Assign statements example
// Demonstrates the limited behavioral SystemVerilog support

module assign_statements(a, b, y_and, y_or, y_xor, y_nand, y_nor, y_xnor, y_not);
  input logic a, b;
  output logic y_and, y_or, y_xor, y_nand, y_nor, y_xnor, y_not;

  // Simple two-input patterns that sv2svg can handle
  assign y_and = a & b;
  assign y_or = a | b;
  assign y_xor = a ^ b;
  assign y_nand = ~(a & b);
  assign y_nor = ~(a | b);
  assign y_xnor = ~(a ^ b);
  assign y_not = ~a;
endmodule