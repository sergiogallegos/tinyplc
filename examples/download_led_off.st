(* Serial-download demonstration. Tags deliberately differ from boot ordering.
   When BTN is released LD2 is OFF; activation starts N from zero. *)
PROGRAM Downloaded
VAR N : DINT; END_VAR
VAR_INPUT BTN : BOOL; END_VAR
VAR_OUTPUT LED : BOOL; END_VAR
N := N + 1;
LED := BTN;
END_PROGRAM
