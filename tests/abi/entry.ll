; Handwritten ABI 2 fixture, not compiler output.
; Schema: INPUT divisor:DINT, OUTPUT quotient:DINT, VAR counter:DINT.
; Deliberately dirty working state on fault: only the supervisor can commit it.
define i32 @fixture_scan(ptr %inputs, ptr %working, i32 %count, ptr %diag) {
entry:
  %col = getelementptr i32, ptr %diag, i32 1
  store i32 0, ptr %diag, align 4
  store i32 0, ptr %col, align 4
  %valid = icmp eq i32 %count, 3
  br i1 %valid, label %run, label %bad_count
bad_count:
  ret i32 4
run:
  %divisor = load i32, ptr %inputs, align 4
  %counter = getelementptr i32, ptr %working, i32 2
  %old = load i32, ptr %counter, align 4
  %new = add i32 %old, 1
  store i32 %new, ptr %counter, align 4
  %zero = icmp eq i32 %divisor, 0
  br i1 %zero, label %fault, label %divide
fault:
  store i32 7, ptr %diag, align 4
  store i32 12, ptr %col, align 4
  ret i32 5
divide:
  %min = icmp eq i32 %new, -2147483648
  %neg = icmp eq i32 %divisor, -1
  %overflow = and i1 %min, %neg
  %safe = select i1 %overflow, i32 1, i32 %divisor
  %value = sdiv i32 %new, %safe
  %output = getelementptr i32, ptr %working, i32 1
  store i32 %value, ptr %output, align 4
  ret i32 0
}
