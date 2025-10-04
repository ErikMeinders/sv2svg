// Assign statement test - with timing delay
module assign_timing(a, b, y);
  input logic a, b;
  output logic y;

  assign #3 y = a | b;
endmodule
