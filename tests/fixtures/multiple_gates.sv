// Multiple gates test
module multiple_gates(a, b, c, y);
  input logic a, b, c;
  output logic y;

  logic n1, n2;

  AND u1(a, b, n1);
  OR u2(n1, c, n2);
  NOT u3(n2, y);
endmodule
