// Test inline port type specifications
// This tests the issue described in #14

module func( input logic a, b, c,
            output logic y );
  AND u1(a, b, y);
endmodule
