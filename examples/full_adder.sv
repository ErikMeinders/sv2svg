// Full adder example
// Demonstrates a complete 1-bit full adder using basic gates

module full_adder(a, b, cin, sum, cout);
  input logic a, b, cin;
  output logic sum, cout;

  logic ab_xor, ab_and, ac_and, bc_and, ab_ac_or;

  // Sum logic: sum = a ^ b ^ cin
  XOR u1(a, b, ab_xor);
  XOR u2(ab_xor, cin, sum);

  // Carry out logic: cout = (a & b) | (a & cin) | (b & cin)
  AND u3(a, b, ab_and);
  AND u4(a, cin, ac_and);
  AND u5(b, cin, bc_and);
  OR u6(ab_and, ac_and, ab_ac_or);
  OR u7(ab_ac_or, bc_and, cout);
endmodule