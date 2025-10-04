// Comprehensive test for inline port specifications
// Tests multiple patterns: input without type, output with type, mixed

module comprehensive(input a,
                     input logic b, c,
                     output logic x, y,
                     output z);
  // Inputs: a, b, c
  // Outputs: x, y, z
  AND u1(a, b, x);
  OR u2(b, c, y);
  XOR u3(a, c, z);
endmodule
