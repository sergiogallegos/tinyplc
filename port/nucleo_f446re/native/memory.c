/* Freestanding C library primitives used by this kernel configuration. */
#include <stddef.h>
#include <stdint.h>
void *memset(void *dest, int value, size_t count)
{
    unsigned char *p = dest;
    while (count--)
        *p++ = (unsigned char)value;
    return dest;
}
void *memcpy(void *dest, const void *src, size_t count)
{
    unsigned char *d = dest;
    const unsigned char *s = src;
    while (count--)
        *d++ = *s++;
    return dest;
}
int memcmp(const void *left, const void *right, size_t count)
{
    const unsigned char *a = left, *b = right;
    while (count--) {
        if (*a != *b)
            return *a < *b ? -1 : 1;
        ++a;
        ++b;
    }
    return 0;
}
void *memmove(void *dest, const void *src, size_t count)
{
    unsigned char *d = dest;
    const unsigned char *s = src;
    /* Integer ordering avoids relational comparison of unrelated C objects. */
    if ((uintptr_t)d > (uintptr_t)s) {
        while (count) {
            --count;
            d[count] = s[count];
        }
    } else {
        for (size_t i = 0; i < count; ++i)
            d[i] = s[i];
    }
    return dest;
}
