#include "tinyplc/loader.h"
/* One static instance in privileged RAM; code arrays occupy separate slots. */
_Static_assert(sizeof(tinyplc_loader)<=24u*1024u,"loader exceeds 24 KiB budget");
tinyplc_loader tinyplc_loader_budget;
