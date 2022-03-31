# Transition from Lenni

- Now that we have seen an attack and a mitigation for Meltdown-type vulnerabilities

- I am going to discuss the other major type of Transient Execution Attacks

- Which are Spectre-Type Attacks

## Spectre-Type Attack Demo

<!-- Goal of this demonstration is
to show the mechanism behind a typical spectre-type attack
and that it can be executed successfully inside our CPU emulator

this underlying mechanism is that the BPU ...
    that means the attacker causes a mispredicted branch in the victim code
    which then leads to the victim accessing some secret data

in general this also requires code sequences to be present in the victim code
    that allow the attacker to exfiltrate this data
    usually by encoding it into the cache
We will use a contrived example for that, to demonstrate the main point as simple as possible
-->

- Demonstrate mechanism behind Spectre-type attacks

- BPU can be trained for targeted misprediction

- Requires code sequence that encodes leaked value into cache

## Spectre-Type Attack: Overview

- Prepare victim array: 8 elements, all zero

  - Followed by secret value `0x41`

<!-- Conceptually the attacker invokes the victim code, which then -->

- Victim loops over the array and encodes each value in the cache

  - BPU is trained to predict that the loop continues

- Final loop condition will be mispredicted

  - During transient execution: Additional iteration with out-of-bounds index

  - Secret value accessed and encoded into cache

<!-- As we already saw during the Meltdown demo, we can then retrieve the secret value by extracting it from the cache -->

<!-- TODO: Pause for questions here? -->

<!-- So, let's take a look at the code we use to implement this attack -->

## Spectre-Type Attack: Preparation

<!-- TODO: Only include if we need the time -->

<!-- This is how we prepare the victim array
The first part writes zero bytes to the first 8 elements
The last two lines write the secret value of 0x41 just past the array -->

```c
// Set up array at 0x1000, 8 elements, all zero
addi r1, r0, 0x1000
sb r0, r1, 0
sb r0, r1, 1
sb r0, r1, 2
sb r0, r1, 3
sb r0, r1, 4
sb r0, r1, 5
sb r0, r1, 6
sb r0, r1, 7
// Followed by one out-of-bounds 0x41 value
addi r2, r0, 0x41
sb r2, r1, 8
```

## Spectre-Type Attack: Execution

<!-- Now we can continue with the code executed during the actual attack,
Which loops over the array and encodes every element's value into the cache
During the loop,
    register r3 is the length of the array, so fixed at 8, and
    register r2 is the current loop index, which is incremented after each iteration
In the loop body
    we load the value of the current element into register r4
    and then encode it into the cache
        this uses the same method we previously used in the meltdown demo
        we multiply the by 16 by shifting it 4 bits to the left
        and use the result to index into our probe array,
        which in this case is located at address 0x2000
the remaining two lines are the tail of the loop,
    which increment the loop index
    and branch back to the top of the loop,
    if the new index is not equal to the length of the array
-->

```c
// Loop over array, encode every value in cache
addi r2, r0, 0    // r2: Loop index
addi r3, r0, 8    // r3: Array length
loop:
// Load array element
lb r4, r2, 0x1000
// Encode value in cache
slli r4, r4, 4
lb r4, r4, 0x2000
// Increment loop index
addi r2, r2, 1
fence
// Loop while index is in bounds
bne r2, r3, loop
```

# Attack Demo

<!-- Now we actually get to see this attack in action

We start the emulator and load the program that I just showed
We are going to skip over the preparation of the array
    and instead directly look at its results in memory
break add 12        Set breakpoint at first instruction of attack part
continue
show mem 0x1000     Look at victim array at address 0x1000 -> 8 zero bytes followed by the secret value 0x41

Let's continue the attack by single-stepping through the first loop iteration

This was a single loop iteration,
    we are going to skip over the intermediate iterations
    and continue with the supposedly last loop iteration
break add 14
continue ...
-->

<!--
- Step past fence, examine memory to see setup of array

- Single-step through first loop iteration
- Breakpoint at load array element, continue through iterations
- Single-step through last loop iteration
- Examine BPU state before the last branch is queued -> branch will be predicted as taken
- Single-step through additional loop iteration, until the secret is encoded into the cache (address 0x2410)
-->

## Spectre-Type Attack: Mitigation

<!-- There are a couple of mitigations against spectre vulnerabilities,
    which we describe in our report
the one I want to focus on here is
flushing the cache after a rollback
-->

- Flush cache after rollback

- Prevents using cache as transmission channel <!-- from transient execution domain to architectural domain -->

- Implementation: Inject microcode after rollback

  - Inject `flushall` instruction after mispredicted branch

# Mitigation Demo

<!-- Now we activate this mitigation and check if our spectre attack still works

- Edit config
- Show injected program
- Start directly in the last loop iteration
- Single-step until rollback
- See injected flush, observe cache before and after
-->

## Conclusion

- Goal: CPU Emulator

  - Out-of-Order Execution

  - Branch Prediction

  - Transient Execution Attacks

  - Mitigations

<!-- as we have demonstrated today, our CPU emulator reaches all of these goals
and it can even be used to understand mitigations for transient execution attacks -->

## Further Work
