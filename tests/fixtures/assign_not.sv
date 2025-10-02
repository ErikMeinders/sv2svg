// Assign statement test - NOT
module assign_not(a, y);
  input logic a;
  output logic y;

  assign y = ~a;
endmodule
