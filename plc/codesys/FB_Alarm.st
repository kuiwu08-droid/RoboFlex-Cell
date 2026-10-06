FUNCTION_BLOCK FB_Alarm
VAR_INPUT
    Trip : BOOL;
    Code : UINT;
    ResetAccepted : BOOL;
END_VAR
VAR_OUTPUT
    Active : BOOL;
    LatchedCode : UINT;
END_VAR
IF Trip THEN
    IF NOT Active THEN
        LatchedCode := Code;
    END_IF;
    Active := TRUE;
ELSIF ResetAccepted THEN
    Active := FALSE;
    LatchedCode := 0;
END_IF;
END_FUNCTION_BLOCK
