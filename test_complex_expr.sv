module test_complex_expr(a, b, c, y1, y2, y3, y4);
    input a, b, c;
    output y1, y2, y3, y4;

    // Simple expressions (already worked)
    assign y1 = a | b;
    assign y2 = a & c;

    // Complex expressions (new functionality)
    assign y3 = a | b & c;      // Should parse as: a | (b & c) due to precedence
    assign y4 = (a | b) & c;    // Should parse as: (a | b) & c due to parentheses

endmodule
