# Spectre-Type Attack Demo

Now that we have seen an attack and a mitigation for Meltdown-type vulnerabilities
I am going to discuss the other major type of Transient Execution Attacks
Which are Spectre-Type Attacks

## Spectre-Type Attack Demo

Goal of this demonstration is
to show the mechanism behind a typical spectre-type attack
and that it can be executed successfully inside our CPU emulator

this underlying mechanism (of spectre attacks) is that the BPU
    can be trained for targeted misprediction
    that means that the attacker causes a mispredicted branch in victim code
    which then leads to this victim accessing some secret data

usually this also requires certain code sequences to be present in the victim code
    that allow the attacker to exfiltrate this data
    usually by encoding it into the cache
Naturally we will use a contrived example for that, just to demonstrate the main point as simply as possible

## Spectre-Type Attack: Overview

We simulate a victim that uses an array of 8 elements
which store the value 0x01.
In memory this array is followed by the secret value 0x41
    not part of the array, but one byte after it

Conceptually the attacker invokes victim code, which then
    loops over the array and encodes each value into the cache

During this loop the loop condition is always true,
    and thus the BPU is trained to predict that the loop continues

This results in the final loop condition being mispredicted

During the transient execution that follows this misprediction,
    an additional iteration of the loop is performed.
    During this iteration, the loop index is out-of-bounds

Because of this, the secret value is accessed and encoded into cache

As we already saw during the Meltdown demo, we can then retrieve the secret value by extracting it from the cache

So, let's take a look at the code we use to implement this attack

## Spectre-Type Attack: Preparation

This is how we prepare the victim array
The first part writes 0x01 to the first 8 elements
The last two lines write the secret value of 0x41 just past the array

## Spectre-Type Attack: Execution

Now we can continue with the code executed during the actual attack,
    Which loops over the array and encodes every element's value into the cache

During the loop,
    register r3 is the length of the array, so fixed at 8, and
    register r2 is the current loop index, which is incremented after each iteration

In the loop body
    we load the value of the current element into register r4
    and then encode it into the cache
        this uses the same method we previously used in the meltdown demo, in that
        we multiply the value by 16
        and use the result to index into our probe array,
        which in this case is located at address 0x2000

the remaining two lines are the tail of the loop,
    which increment the loop index
    and branch back to the top of the loop,
    as long as the new index is not equal to the length of the array

# Attack Demo

Now we actually get to see this attack in action

We start the emulator and load the program that I just showed,
    with an additional fence instruction that separates the preparation and the actual attack

We are going to skip over the preparation of the array
    and instead directly look at its results in memory

                    To do that, we
break add 12        Set breakpoint at the fence instruction
continue            Continue execution, and then
retire ...          Step until all instructions from the preparation part have retired. After that we
show mem 0x1000     Look at victim array at address 0x1000 -> 8 bytes of 0x01 followed by the secret value 0x41

Let's continue the attack by single-stepping through the first loop iteration
addi r2, r0, 0      initialize current loop index to zero
addi r3, r0, 8      set the length of the array to 8
lb r4, r2, 0x1000   
slli r4, r4, 4      
lb r4, r4, 0x2000   
addi r2, r2, 1      
bne r2, r3, loop    

This was a single loop iteration,
    we are going to skip over the intermediate iterations
    and continue with the supposedly last loop iteration
break add 14
continue ...

- Single-step through last loop iteration
- Examine BPU state before the last branch is queued -> branch will be predicted as taken
- Single-step through additional loop iteration, until the secret is encoded into the cache (address 0x2410)

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
