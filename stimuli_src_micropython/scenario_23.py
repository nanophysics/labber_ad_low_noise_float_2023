def scenario():
    time_ms=500

    IN_disable(0)
    IN_P(IN_P_0V7)

    wait_ms(time_ms)
    
    IN_t(0)
    IN_P(IN_P_1V4)

    wait_ms(time_ms)

    IN_disable(1)
    IN_P(IN_P_0V0)

    wait_ms(time_ms)
    
    IN_t(1)
    IN_P(IN_P_1V4)

