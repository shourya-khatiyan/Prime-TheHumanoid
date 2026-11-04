# Presentation script

Say it like this. Pause where there is a blank line.

---

Hello.

Before I show you the arm, I want to tell you what we were trying to build. Otherwise this table will not make any sense.

We are trying to build a humanoid. A humanoid is a robot with a body like a person. Two arms, two legs, a head. The use is simple. It can do the work you do not want a person standing in. On a factory floor, and in places that are dangerous. A fire, a collapsed building, a plant with gas or chemicals. The robot goes in. A person does not have to.

You have seen them in videos. Almost all of those videos are from China. That is the part people in India already know. What you do not see is India using them. Not in factories, and not in those dangerous jobs. Very few people here are even building one, and the ones who are are still at the start.

It is not that we cannot build a humanoid. The blocker is the components. And every one of those components is basically a company by itself. The motor is one company. The gears are another. The controller is another. You are not buying a robot off a shelf. You are buying from a list of companies, and those companies are not in India.

What people here do not know is what is inside that robot, and what happens when you sit in India and try to build one.

A robot like that moves at the joints. Shoulder, elbow, wrist, hip, knee, ankle. A full body has about eighteen of those main joints, even before you count the fingers. Every one of those joints needs its own part. That part has to be strong, it has to be small enough to fit in the body, and it has to stop where you tell it to stop. If the hip is weak, the robot cannot stand. If the shoulder is sloppy, the hand misses.

That part is called an actuator. You can forget the word after this. It just means the motor and the gears of one joint, made as one piece.

So we made a list, like anyone would.

The hips and the legs have to carry the whole body. For those we needed the strong joints, past 150. The arms can live with smaller ones. Then we went to buy them.

You cannot buy them in India. There is no shop, no website, where a humanoid hip is in stock and you order it the way you order a motor for a college project. We looked. It is not there.

The joints that these robots actually use come from outside. The expensive proper ones come from companies like Harmonic Drive. When we priced a full body, hips, legs, and arms, the bill crossed 20 lakh. And that was only the joints. They were still not here. You request a quote, you wait, you import.

Then we did the obvious next thing. China. You have seen the robots, so you assume the parts must be cheap there. They are cheaper, because those companies make the motor, the gears, and the electronics at home, in large numbers. We priced a full body on those too. For us it still went above 20 lakh. And it was still a parcel from another country. If one joint fails, the project stops until the next shipment.

That is the actual problem. We did not get stuck because we could not imagine the robot. We got stuck because the one part every joint needs is too expensive, and India does not make it.

So we stopped collecting quotes. We decided to make the joint ourselves. DA sir has been guiding us on that.

Now, what we could afford was very small.

The motor for a joint like this is not a usual dc motor that you might have seen in toys. A toy motor has brushes that rub and wear out. We needed a brushless motor, the kind used in drones. Stronger for its size, and you can tell it how hard to push. We could only bought two since these are imported as well and were very expensive.

These motors do not run with the battery directly. they needs a motor controller. We were using a Chinese one. It got damaged. When we ordered a replacement, they gave us a wait of 17 days. The arm just sits there for those 17 days. Ours now is one ODrive board that is a field oriented controller, and it can run two motors. Two motors and that one board were all we could buy with our budget because we also had to purchase other components.

So we built an arm. This one.

Two joints. A shoulder and an elbow. The shoulder is our own actuator, the first one we made. It is compact. In normal use it is about 30. When it has to push harder, about 50. We built that joint for around 17,000 rupees. That includes the motor. It does not include the ODrive. Put that next to the bill I just told you. We were being quoted more than 20 lakh for a set of joints from outside. One joint of ours, made here, is about 17,000.

The elbow is the second motor. It turns the forearm directly. We did not build a second gearbox for it. We had two motors and one board, and we spent the gearbox effort on the shoulder.

After that first joint, we designed the next one. Same motor. The gears are different. They are cycloidal, which only means many teeth carry the load together, instead of one tooth taking all of it. The motor turns 45 times, and the joint turns once. With that, normal use comes to around 50, and a short hard push goes past 60.

I do not want to dress that up. You are not looking at a robot that walks. You are looking at the part India does not sell. We made it, at a price we can say in this room without flinching.

What we want to do with it is also simple.

We will finish this joint so that another lab can buy it from us, instead of waiting on Japan or China. Then we will make the brushless motor here. Then we will make our own controller, so we are not buying the ODrive either. Those three things, the joint, the motor, and the board, are what stopped us. A college still cannot find them in India.

We will not keep them on our own bench. We will start with schools. Short workshops, on this part, not on a video. The people who will build the next ten years are in school now, and today they only know the Chinese robot. If they see the joint was made here, some of them start earlier. That is the base. A country grows from there.

Then colleges, private and government. And the big institutions, the IITs, IISc, whichever research lab will sit with us. We will go to as many as we can. The ask is small. Use the part. Let your students build on something they can actually get.

The point is a stock in India. Joints, motors, boards, here, so more people can try more things and the work moves faster. We are not short of people who can do this. What stops them is the market. The parts are not available. China moved ahead because a student there can order the joint the same week. Our students can mostly watch. If the parts are made here, we stop watching and start building with them.

This arm is the first step. Two motors. One board. One joint we made ourselves, for about 17,000 rupees. The next one is already stronger. The body comes after the parts exist.

Thank you. I can walk you through the arm if you want to see where the joint sits.

---

## If they ask

**What is an actuator, again?**
The motor and the gears of one joint, as one piece. Shoulder, elbow, hip, knee. Each one needs its own.

**Why not use a normal motor?**
A normal small motor has brushes that wear out, and it is weak for this job. A brushless motor is what drones use. Stronger for its size. It needs a controller. That controller is the ODrive on our bench, and ours can run two motors.

**China is cheaper. Why not just import?**
We tried that route for a full body. It still crossed 20 lakh, and every replacement is a shipment. The hip we needed is a much stronger joint than the cheap ones in the videos. We want the next team in India to buy this from here.

**Is 17,000 real?**
That is what this joint cost us to build, motor included, controller not included. It is a first piece, not a factory price for a hundred. The point is the order of magnitude. Thousands, not lakhs.

**Your new joint is 50. The leg needed 150. So you are not done.**
Correct. The leg still needs a bigger joint. This arm was what two motors could build. The new gearbox is us climbing. Around 50 now, past 60 on a short push, same motor. The hip comes after we can make this one properly.

**Someone in India already makes these.**
If they do, we could not buy one. We could not find a hip past 150, in stock, with a price. What exists today did not solve our bill. That is why this joint is on the table.

**Why schools?**
They are not going to build the humanoid. They should see that this part is made here, and that this is work people in India do. The colleges and the IITs build the machines. School is where someone decides to be the one who builds them.
