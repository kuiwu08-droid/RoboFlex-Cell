FUNCTION_BLOCK FB_Robot
VAR_INPUT
    Execute : BOOL;
    SafeEnable : BOOL;
    Reset : BOOL;
    Ready : BOOL;
    Running : BOOL;
    Complete : BOOL;
    RobotError : BOOL;
END_VAR
VAR_OUTPUT
    Start : BOOL;
    Ack : BOOL;
    Stop : BOOL;
    Done : BOOL;
    Error : BOOL;
    ErrorId : UINT;
END_VAR
VAR
    Phase : UINT;
    StartEdge : R_TRIG;
    StartTimer : TON;
    MotionTimer : TON;
    AckTimer : TON;
END_VAR

StartEdge(CLK := Execute);
StartTimer(IN := Phase = 10, PT := T#500ms);
MotionTimer(IN := Phase = 20, PT := T#6s);
AckTimer(IN := Phase = 30, PT := T#500ms);
Start := FALSE;
Ack := FALSE;
Stop := NOT SafeEnable;

IF Reset AND SafeEnable THEN
    Phase := 0;
    Done := FALSE;
    Error := FALSE;
    ErrorId := 0;
ELSIF NOT SafeEnable THEN
    Phase := 0;
    Done := FALSE;
ELSIF RobotError THEN
    Error := TRUE;
    ErrorId := 3;
END_IF;

IF SafeEnable AND NOT Reset AND NOT Error THEN
    CASE Phase OF
        0:
            IF StartEdge.Q THEN
                IF Ready AND NOT Complete AND NOT Running THEN
                    Phase := 10;
                ELSE
                    Error := TRUE;
                    ErrorId := 3;
                END_IF;
            END_IF;
        10:
            Start := TRUE;
            IF Running THEN
                Start := FALSE;
                Phase := 20;
            ELSIF StartTimer.Q THEN
                Error := TRUE;
                ErrorId := 4;
            END_IF;
        20:
            IF Complete AND NOT Running THEN
                Phase := 30;
            ELSIF MotionTimer.Q THEN
                Error := TRUE;
                ErrorId := 4;
            END_IF;
        30:
            Ack := TRUE;
            IF NOT Complete AND Ready THEN
                Ack := FALSE;
                Done := TRUE;
                Phase := 40;
            ELSIF AckTimer.Q THEN
                Error := TRUE;
                ErrorId := 4;
            END_IF;
        40:
            IF NOT Execute THEN
                Done := FALSE;
                Phase := 0;
            END_IF;
    END_CASE;
END_IF;
IF Error THEN
    Start := FALSE;
    Ack := FALSE;
    Stop := TRUE;
END_IF;
END_FUNCTION_BLOCK
