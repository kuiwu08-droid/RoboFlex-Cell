FUNCTION_BLOCK FB_Gripper
VAR_INPUT
    CloseRequest : BOOL;
    ClosedFeedback : BOOL;
    OpenFeedback : BOOL;
    SafeEnable : BOOL;
    Reset : BOOL;
END_VAR
VAR_OUTPUT
    CloseValve : BOOL;
    AtPosition : BOOL;
    Error : BOOL;
END_VAR
VAR
    FeedbackTimer : TON;
END_VAR
(* Hold the last valve command on a software safety stop; never drop a part.
   A physical safety circuit requires an independently assessed pneumatic design. *)
IF SafeEnable THEN
    CloseValve := CloseRequest;
END_IF;
AtPosition := (CloseRequest AND ClosedFeedback) OR (NOT CloseRequest AND OpenFeedback);
FeedbackTimer(IN := SafeEnable AND NOT AtPosition, PT := T#500ms);
IF Reset THEN
    Error := FALSE;
ELSIF FeedbackTimer.Q THEN
    Error := TRUE;
END_IF;
END_FUNCTION_BLOCK
