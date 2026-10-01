PROGRAM Fault
VAR_INPUT
    BTN : BOOL;
END_VAR
VAR_OUTPUT
    LED : BOOL;
END_VAR
VAR
    n : DINT;
END_VAR
(* The fault must prevent both the TRUE output and n=123 from committing. *)
LED := TRUE;
n := 123;
n := n / 0;
END_PROGRAM
