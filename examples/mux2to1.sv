// 2:1 Multiplexer example
// Demonstrates a 2-to-1 multiplexer using basic gates
// y = sel ? b : a

module mux2to1(a, b, sel, y);
  input logic a, b, sel;
  output logic y;

  logic sel_n, a_sel_n, b_sel;

  // Invert select signal
  NOT u1(sel, sel_n);

  // AND gates for selection
  AND u2(a, sel_n, a_sel_n);
  AND u3(b, sel, b_sel);

  // OR gate for output
  OR u4(a_sel_n, b_sel, y);
endmodule