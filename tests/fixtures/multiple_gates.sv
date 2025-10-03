// Multiple gates test

module multiple_gates(a, b, c, y);
  
  input  logic a, b, c;
  output logic y;

  logic s1,  s2, s3;

    AND u1(a,  b,  s1);
  
    OR  u2(s1, c,  s2);

    XOR u3(s1, s2, s3);
  
    NOT u4(s3, y);
    
endmodule
