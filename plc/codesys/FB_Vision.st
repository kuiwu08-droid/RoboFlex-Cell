FUNCTION_BLOCK FB_Vision
VAR_INPUT
    Execute : BOOL;
    SafeEnable : BOOL;
    Connected : BOOL;
    ResultValid : BOOL;
    ResultOK : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    Trigger : BOOL;
    Ack : BOOL;
    Done : BOOL;
    Error : BOOL;
    ErrorId : UINT;
END_VAR
VAR
    Phase : UINT;
    Edge : R_TRIG;
    ResultTimer : TON;
    ClearTimer : TON;
END_VAR
Edge(CLK := Execute);
ResultTimer(IN := Phase = 10, PT := T#1s);
ClearTimer(IN := Phase = 20, PT := T#500ms);
Trigger := FALSE;
Ack := FALSE;
IF Reset OR NOT SafeEnable THEN
    Phase := 0;
    Done := FALSE;
    Error := FALSE;
    ErrorId := 0;
ELSIF NOT Error THEN
    CASE Phase OF
        0:
            IF Edge.Q THEN
                IF Connected AND NOT ResultValid THEN
                    Phase := 10;
                ELSE
                    Error := TRUE;
                    ErrorId := 1;
                END_IF;
            END_IF;
        10:
            Trigger := TRUE;
            IF NOT Connected THEN
                Error := TRUE;
                ErrorId := 1;
            ELSIF ResultValid THEN
                Trigger := FALSE;
                IF ResultOK THEN
                    Phase := 20;
                ELSE
                    Error := TRUE;
                    ErrorId := 2;
                END_IF;
            ELSIF ResultTimer.Q THEN
                Error := TRUE;
                ErrorId := 2;
            END_IF;
        20:
            Ack := TRUE;
            IF NOT ResultValid THEN
                Ack := FALSE;
                Done := TRUE;
                Phase := 30;
            ELSIF ClearTimer.Q THEN
                Error := TRUE;
                ErrorId := 2;
            END_IF;
        30:
            IF NOT Execute THEN
                Done := FALSE;
                Phase := 0;
            END_IF;
    END_CASE;
END_IF;
IF Error THEN
    Trigger := FALSE;
    Ack := FALSE;
END_IF;
END_FUNCTION_BLOCK
