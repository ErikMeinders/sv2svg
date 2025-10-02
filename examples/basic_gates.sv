// Basic logic gates example
// Demonstrates AND, OR, NOT gates using gate instantiations

module basic_gates(a, b, y_and, y_or,y );
  input logic a, b;
  output logic y_and, y_or,y;

  // Basic gates
  AND u1(a, b, y_and);
  OR u2(a, b, y_or);

  y = a & b;
endmodule