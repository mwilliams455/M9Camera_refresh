// Host-only stand-in for the NDK logging header used by dngCreator.cpp.
#pragma once
#define ANDROID_LOG_DEBUG 3
#define ANDROID_LOG_ERROR 6
#define ANDROID_LOG_WARN 5
#define ANDROID_LOG_INFO 4
#define __android_log_print(...) 0
