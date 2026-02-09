// Compatibility shims for linking MSYS2-built static libraries with WinLibs MinGW
// Provides __imp__vsnprintf symbol expected by MSYS2-built OpenSSL.
// (__imp__setjmp is handled via --defsym linker flag)

#include <stdio.h>
#include <stdarg.h>

// Provide _vsnprintf as a real function that OpenSSL can import-call
// The __imp__ prefix tells the linker this is the import address table entry
int __cdecl compat_vsnprintf(char *buf, size_t count, const char *fmt, va_list ap) {
    return vsnprintf(buf, count, fmt, ap);
}

// Create the __imp__vsnprintf pointer that the MSYS2 OpenSSL lib expects
typedef int (__cdecl *vsnprintf_fn)(char*, size_t, const char*, va_list);
vsnprintf_fn __imp__vsnprintf = compat_vsnprintf;
