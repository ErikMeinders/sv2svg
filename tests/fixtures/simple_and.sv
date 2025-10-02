// Simple AND gate test
module simple_and(a, b, y);
  input logic a, b;
  output logic y;

  AND u1(a, b, y);
endmodule
