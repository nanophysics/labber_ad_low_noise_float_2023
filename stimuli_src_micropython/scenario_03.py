# Scenario: trigger
def scenario():
    IN_t(1)
    IN_P(IN_P_1V4)
    wait_ms(50)
    IN_t(0)
    IN_P(IN_P_0V0)