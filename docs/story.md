# Story

This is the account we tell. The speech is in `docs/presentation-script.md`. Same story, written down.

## What we are building

We are building a humanoid. A robot with a body like a person. Two arms, two legs, a head.

People in India have seen these robots in videos. Almost all of those videos are from China. What they have not seen is what is inside, and what happens when you try to build one from here.

The robot moves at the joints. Shoulder, elbow, wrist, hip, knee, ankle. A full body has about eighteen main joints, before the fingers. Each joint needs its own part. That part has to be strong, small enough to fit in the limb, and able to stop where it is told. If the hip is weak, the robot cannot stand. If the shoulder is loose, the hand misses.

That part is an actuator. The motor and the gears of one joint, made as one piece.

## What we needed, and what we found

The hips and the legs carry the body, so those joints had to be the strong ones, past 150. The arms could be smaller. We made that list and went to buy it.

India does not stock it. There is no shop and no site where a student orders a humanoid hip the way they order a motor for a college project. We looked. For the strength we needed, it was not there.

The joints these robots use come from outside. The expensive proper ones come from companies like Harmonic Drive. A full body, hips, legs, and arms, crossed 20 lakh for the joints alone. They were still not here. A quote, a wait, an import.

China was the obvious next look. The robots are famous, and the parts are cheaper there, because those companies make the motor, the gears, and the electronics at home, in volume. A full body on that route still went above 20 lakh for us. Cheaper than the first quote, still more than we could pay, and still a parcel. If one joint fails, the project waits on the next shipment.

We did not get stuck because we could not imagine the robot. We got stuck because the part every joint needs is too expensive, and India does not make it.

## What we could actually buy

We stopped collecting quotes and decided to make the joint ourselves.

The motor inside that joint is its own problem. It is not a toy motor. A toy motor has brushes, small pieces of carbon that rub inside. They wear out, they spark, and the motor is bad at holding still under load. This job needs a brushless motor, the kind used in drones. No brushes. Strong for its size, and you can tell it how hard to push. We bought two, 90 KV, the size a shoulder needs. They are imported, and they are costly.

A brushless motor does not run from a battery alone. It needs a controller. Ours is an ODrive. One board, and it is dual, so it runs two motors. Two motors and that one board were the whole budget. Two joints, not a body of eighteen.

## What we built

The machine is an arm. Shoulder and elbow.

The shoulder is our first actuator. Compact. On the same scale where the leg we wanted was past 150, this joint is about 30 in normal use and about 50 when it pushes harder. We built it for around 17,000 rupees. That includes the motor. It does not include the ODrive. The joints we were quoted from outside were a bill in the lakhs. One joint of ours is about 17,000.

The elbow is the second motor, turning the forearm directly. We did not build a second gearbox. The board runs both. Shoulder through our gears, elbow straight off the motor.

The next design keeps the same motor and changes the gears. They are cycloidal: many teeth share the load, instead of one pair taking all of it. The motor turns 45 times and the joint turns once. Normal use comes to around 50. A short hard push goes past 60.

This is not a walking robot. It is the part India does not sell, made here, at a price we can say out loud.

## Where we take it

We finish this joint so another lab can buy it from us, instead of waiting on Japan or China. Then we make the brushless motor here. Then we make our own controller, so we are not buying the ODrive either. The joint, the motor, and the board are the three things that stopped us. A college still cannot find them in India.

We will not keep them on our own bench.

Schools come first. Short workshops, on this part, not on a video. The people who will build the next ten years are in school now, and today they only know the Chinese robot. If they see the joint was made here, some of them start earlier. A country grows from there.

Then colleges, private and government. Then the big institutions, the IITs, IISc, and whichever research lab will sit with us. We go to as many as we can. The ask is small. Use the part. Let the students build on something they can actually get.

The point is a stock in India. Joints, motors, and boards, here, so more people can try more things and the work moves faster. We are not short of people who can do this. What stops them is the market. The parts are not available. China moved ahead because a student there can order the joint the same week. Our students can mostly watch. If the parts are made here, we stop watching and start building with them.

The arm is the first step. Two motors. One board. One joint we made for about 17,000 rupees. The next one is already stronger. The body comes after the parts exist.
