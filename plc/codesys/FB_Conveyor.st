FUNCTION_BLOCK FB_Conveyor
VAR_INPUT
    RunRequest : BOOL;
    SafeEnable : BOOL;
    JamDetected : BOOL;
END_VAR
VAR_OUTPUT
    MotorRun : BOOL;
END_VAR
MotorRun := RunRequest AND SafeEnable AND NOT JamDetected;
END_FUNCTION_BLOCK
