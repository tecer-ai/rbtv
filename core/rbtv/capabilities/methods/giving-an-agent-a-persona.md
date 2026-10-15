# Giving an agent a persona

The result: an agent with a persona the owner chose, made of a name, a short profile, a story and a realistic profile photo that shows beside its messages. The persona is inspirational. The agent's `prompt.md` says how it works and stays the serious part; the persona is built on top of it and never changes it. When the interview turns up a new job for the agent, propose that as a separate change to `prompt.md`.

Inputs:

- The agent's folder, with its `prompt.md` and `agent.json`.
- An image host: a public place the owner lets you publish images to, and the link pattern for a published image. When the task does not supply one, ask the owner for it before publishing; the persona can be agreed without it.
- The installation's persona style, when the task supplies one: a colour or detail every portrait carries, the world the agents' stories are set in, and any other agent's portrait to stay consistent with. Without one, agree the style with the owner in the interview.

## 1. Interview the owner

Read the agent's `prompt.md` and `agent.json` first, and do not ask what they already answer. Then ask the owner, in one or two grouped messages:

1. Who is this agent to you, in one sentence: a colleague, an assistant, a guardian, a toy?
2. What image do you have in your head: a person, an age, a gender, a profession, a character from a game, a film or mythology?
3. What feel: serious or playful, warm or sharp, worker or leader, realistic or a little mythic?
4. Where does this agent come from in the agents' world, and what does it do there for the others?
5. What must the name or image not be?

Then brainstorm with the owner and propose, with a recommendation and its reason:

- three name options, each with its meaning and what it evokes;
- the profile: what the agent does, in plain words, from `prompt.md`;
- the story, in four or five sentences;
- the image: the person, their clothing, the place behind them and one small symbolic detail.

Generate no image until the owner has picked the name and agreed the image.

## 2. Make the portrait

Every agent's portrait is a realistic profile photograph of a different person in their own place. Write the prompt from this template:

```
A realistic photograph: a professional profile photo, as if taken with a full-frame camera and an 85mm lens at f/1.8. Real skin texture, natural light, shallow depth of field, the background softly blurred. A tight headshot: the face and hair fill most of the square, cropped just below the shoulders. Square 1024x1024. No text, no logos, no border. One person only, an original face that is not a likeness of any real person.

Pose: <the body and head angle, and the posture>.

The person: "<name>", <who they are>. <Age, hair, face, expression>. <Clothing, with the style's detail when there is one>.

Setting behind them, blurred: <a place that says what the agent does>.
```

- Give each agent a different pose from the agents before it: turn the body to one side or the other, turn the face, lean or sit upright. The same frontal pose on every agent makes them look generated.
- Generate two drafts: the model `cast route --caps image` names, run with `cast api <model> 1 --image -f <prompt file> --output-folder <folder>`. Show them side by side, each with a copy at 36 pixels, the size of a chat icon, and let the owner choose. Keep both drafts.
- To change a draft the owner likes, send it back with `--input-image` and say what to keep and what to change; regenerating from text loses the person.
- When the face is too small, ask for a closer headshot with the photo as input, or crop around the face. Keep the clothing and its detail in the frame.
- A name taken from a real person tends to produce that person's face. Check the draft, and redo it when it resembles them.

## 3. Make it live

1. Publish the chosen photo to the image host, and keep both drafts and the prompt beside the installation's other portraits.
2. Set the avatar to the photo's public link: `rbtv agent configure <agent> --avatar <link>`. A chat client keeps a picture cached by its link: when you replace a picture, publish it under a new link or add a version, such as `?v=2`, and set the avatar again.
3. Use the persona's name as the agent's name when the agent is created. When the owner keeps an existing agent's internal name, for example a main agent reached on several channels, set the name people see instead: `rbtv agent configure <agent> --external-name <Name>`.
4. Tell the owner the change shows from the agent's next message; earlier messages keep the name and picture they were sent with.
