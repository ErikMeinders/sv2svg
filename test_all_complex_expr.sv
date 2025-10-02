module test_all_complex_expr(a, b, c, d, out1, out2, out3, out4, out5, out6, out7, out8);
    input a, b, c, d;
    output out1, out2, out3, out4, out5, out6, out7, out8;

    // Simple expressions (baseline)
    assign out1 = a | b;
    assign out2 = a & c;

    // Complex expressions with precedence
    assign out3 = a | b & c;        // Should parse as: a | (b & c)
    assign out4 = a & b | c;        // Should parse as: (a & b) | c

    // Parentheses override precedence
    assign out5 = (a | b) & c;      // Should parse as: (a | b) & c
    assign out6 = a & (b | c);      // Should parse as: a & (b | c)

    // Multiple operators
    assign out7 = a & b | c & d;    // Should parse as: (a & b) | (c & d)

    // Negation patterns
    assign out8 = ~(a & b | c);     // Should parse as: NOT((a & b) | c)

endmodule
