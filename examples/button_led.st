PROGRAM Main
VAR_INPUT
    BTN : BOOL;
END_VAR
VAR_OUTPUT
    LED : BOOL;
END_VAR
VAR
    n : DINT;
END_VAR
(* n increments every scan while BTN is TRUE, not once per press. *)
IF BTN THEN
    n := n + 1;
END_IF;
LED := NOT BTN;
END_PROGRAM
