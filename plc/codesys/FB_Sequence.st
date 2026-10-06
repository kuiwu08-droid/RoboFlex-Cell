FUNCTION_BLOCK FB_Sequence
VAR_INPUT
    StartButton : BOOL;
    StopButton : BOOL;
    ResetButton : BOOL;
    ManualPartClear : BOOL;
    SafetyOK : BOOL;
    HeartbeatOK : BOOL;
    PartDetected : BOOL;
    JamDetected : BOOL;
    VisionDone : BOOL;
    VisionError : BOOL;
    VisionErrorId : UINT;
    RobotDone : BOOL;
    RobotError : BOOL;
    RobotErrorId : UINT;
    GripperClosed : BOOL;
    GripperOpen : BOOL;
    GripperError : BOOL;
    QualityOK : BOOL;
END_VAR
VAR_OUTPUT
    State : UINT; (* 0 idle, 30 wait, 40 vision, 50 pick, 55 grip, 60 place,
                     65 release, 70 check, 75 home, 80 complete, 900 error *)
    ConveyorRequest : BOOL;
    VisionExecute : BOOL;
    RobotExecute : BOOL;
    JobNumber : UINT; (* 1 pick, 2 place, 3 home; pose data sent separately *)
    CloseRequest : BOOL;
    AlarmCode : UINT;
    ResetAccepted : BOOL;
    OKCount : UDINT;
    NGCount : UDINT;
END_VAR
VAR
    StartEdge : R_TRIG;
    ResetEdge : R_TRIG;
    StateTimer : TON;
    LastState : UINT;
    TripCode : UINT;
END_VAR

StartEdge(CLK := StartButton);
ResetEdge(CLK := ResetButton);
StateTimer(IN := State = LastState AND State <> 0 AND State <> 900, PT := T#2s);
LastState := State;
ResetAccepted := FALSE;
TripCode := 0;
ConveyorRequest := FALSE;
VisionExecute := FALSE;
RobotExecute := FALSE;

IF NOT SafetyOK THEN
    TripCode := 10; (* actual E-stop/door distinction belongs in mapped safety status *)
ELSIF State <> 0 AND State <> 900 THEN
    IF NOT HeartbeatOK THEN TripCode := 7;
    ELSIF StopButton THEN TripCode := 13;
    ELSIF RobotError THEN TripCode := RobotErrorId;
    ELSIF VisionError THEN TripCode := VisionErrorId;
    ELSIF GripperError THEN TripCode := 5;
    ELSIF JamDetected THEN TripCode := 9;
    END_IF;
END_IF;

IF TripCode <> 0 AND State <> 900 THEN
    AlarmCode := TripCode;
    State := 900;
END_IF;

CASE State OF
    0:
        IF StartEdge.Q AND SafetyOK AND HeartbeatOK AND NOT JamDetected THEN State := 30; END_IF;
    30:
        ConveyorRequest := TRUE;
        IF PartDetected THEN
            ConveyorRequest := FALSE;
            State := 40;
        ELSIF StateTimer.Q THEN
            AlarmCode := 8;
            State := 900;
        END_IF;
    40:
        VisionExecute := TRUE;
        IF VisionDone THEN State := 50; END_IF;
    50:
        JobNumber := 1;
        RobotExecute := TRUE;
        IF RobotDone THEN State := 55; END_IF;
    55:
        CloseRequest := TRUE;
        IF GripperClosed THEN State := 60; END_IF;
    60:
        JobNumber := 2;
        RobotExecute := TRUE;
        IF RobotDone THEN State := 65; END_IF;
    65:
        CloseRequest := FALSE;
        IF GripperOpen THEN State := 70; END_IF;
    70:
        IF QualityOK THEN State := 75;
        ELSIF StateTimer.Q THEN
            NGCount := NGCount + 1;
            AlarmCode := 6;
            State := 900;
        END_IF;
    75:
        JobNumber := 3;
        RobotExecute := TRUE;
        IF RobotDone THEN State := 80; END_IF;
    80:
        OKCount := OKCount + 1;
        State := 30;
    900:
        IF ResetEdge.Q AND SafetyOK AND HeartbeatOK AND NOT JamDetected AND ManualPartClear THEN
            ResetAccepted := TRUE;
            CloseRequest := FALSE;
            AlarmCode := 0;
            State := 0;
        END_IF;
END_CASE;
IF State = 900 THEN
    ConveyorRequest := FALSE;
    VisionExecute := FALSE;
    RobotExecute := FALSE;
END_IF;
END_FUNCTION_BLOCK
