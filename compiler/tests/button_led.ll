; tinyplc Rust frontend: PROGRAM MAIN
; Research scan ABI v1; target selected by the LLVM driver.
@tinyplc_abi_version = constant i32 1
@tinyplc_tag_count = constant i32 3
@tinyplc_tag_types = constant [3 x i8] [i8 1, i8 1, i8 2]
@tinyplc_tag_classes = constant [3 x i8] [i8 1, i8 2, i8 3]
@tinyplc_tag_names = constant [3 x [32 x i8]] [[32 x i8] c"BTN\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00", [32 x i8] c"LED\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00", [32 x i8] c"N\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00\00"]

define i32 @tinyplc_scan(ptr %cells, i32 %count, ptr %diag) {
entry:
  %diag_col = getelementptr i32, ptr %diag, i32 1
  store i32 0, ptr %diag, align 4
  store i32 0, ptr %diag_col, align 4
  %v0 = icmp uge i32 %count, 3
  br i1 %v0, label %prepare, label %bad_count
bad_count:
  ret i32 4
prepare:
  %p0 = getelementptr i32, ptr %cells, i32 0
  %w0 = alloca i32, align 4
  %initial0 = load i32, ptr %p0, align 4
  store i32 %initial0, ptr %w0, align 4
  %p1 = getelementptr i32, ptr %cells, i32 1
  %w1 = alloca i32, align 4
  %initial1 = load i32, ptr %p1, align 4
  store i32 %initial1, ptr %w1, align 4
  %p2 = getelementptr i32, ptr %cells, i32 2
  %w2 = alloca i32, align 4
  %initial2 = load i32, ptr %p2, align 4
  store i32 %initial2, ptr %w2, align 4
  %v1 = icmp ule i32 %initial0, 1
  br i1 %v1, label %bool_ok0, label %bool_fault0
bool_fault0:
  store i32 3, ptr %diag, align 4
  store i32 5, ptr %diag_col, align 4
  store i32 0, ptr %p1, align 4
  ret i32 8
bool_ok0:
  %v2 = icmp ule i32 %initial1, 1
  br i1 %v2, label %bool_ok1, label %bool_fault1
bool_fault1:
  store i32 6, ptr %diag, align 4
  store i32 5, ptr %diag_col, align 4
  store i32 0, ptr %p1, align 4
  ret i32 8
bool_ok1:
  %v4 = load i32, ptr %w0, align 4
  %v5 = icmp ne i32 %v4, 0
  br i1 %v5, label %then6, label %else6
then6:
  %v7 = load i32, ptr %w2, align 4
  %v8 = add i32 %v7, 1
  store i32 %v8, ptr %w2, align 4
  br label %end3
else6:
  br label %end3
end3:
  %v9 = load i32, ptr %w0, align 4
  %v10 = xor i32 %v9, 1
  store i32 %v10, ptr %w1, align 4
  %v11 = load i32, ptr %w1, align 4
  store i32 %v11, ptr %p1, align 4
  %v12 = load i32, ptr %w2, align 4
  store i32 %v12, ptr %p2, align 4
  ret i32 0
}
