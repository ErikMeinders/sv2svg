// Test mixed inline and standalone port declarations

module mixed_example(input logic x, y,
                     output logic z);
  // This module uses inline declarations in the header
  AND u1(x, y, z);
endmodule
