// PhoneWalker Command Handler System
#ifndef COMMAND_HANDLER_H
#define COMMAND_HANDLER_H

#include <Arduino.h>
#include "servo_manager.h"

// Command function pointer type
typedef void (*CommandFunction)(const String& args);

// Command definition structure
struct Command {
  char key;
  const char* name;
  const char* description;
  CommandFunction function;
  bool show_in_help;
};

// System modes
enum SystemMode {
  MODE_TRANSPARENT,
  MODE_AUTONOMOUS,
  MODE_TESTING,
  MODE_DANCING
};

class CommandHandler {
private:
  Command* commands;
  int command_count;
  SystemMode current_mode;
  String command_buffer;

  // Built-in command functions
  static void cmdHelp(const String& args);
  static void cmdTransparent(const String& args);
  static void cmdScan(const String& args);
  static void cmdPing(const String& args);
  static void cmdEnable(const String& args);
  static void cmdMove(const String& args);
  static void cmdRead(const String& args);
  static void cmdCenter(const String& args);
  static void cmdStatus(const String& args);
  static void cmdTest(const String& args);
  static void cmdDance(const String& args);
  static void cmdStop(const String& args);
  static void cmdConfig(const String& args);
  static void cmdDebug(const String& args);

  void registerBuiltinCommands();
  void handleTransparentMode();

public:
  CommandHandler();
  void begin();
  void update(); // Call in main loop
  void setMode(SystemMode mode);
  SystemMode getMode();
  void processCommand(char cmd, const String& args = "");
  void addCommand(char key, const char* name, const char* description, CommandFunction func, bool show_in_help = true);
  void removeCommand(char key);
};

// Global command handler instance
extern CommandHandler cmdHandler;

#endif