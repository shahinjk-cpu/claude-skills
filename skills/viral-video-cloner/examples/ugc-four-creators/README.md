# One UGC ad, four creators

The same selfie product clip recreated four times: a new creator and a new setting each time (a cafe, a parked car, a rooftop at sunset, a home office), with the same tumbler, the same pitch and the same hand movements.

|  |  |
| --- | --- |
| Mode | Batch (four motion-transfer runs from one plan template) |
| Output | 9:16 · 8 s · 720p, four versions |
| Cost | ≈8.7 credits per version (measured in October 2026) |
| Reference images | Per version: 1 = the creator (`refs/<a-d>-1-creator.jpg`), 2 = the tumbler ([`refs/2-tumbler.jpg`](refs/2-tumbler.jpg)), 3 = the place (`refs/<a-d>-3-place.jpg`) |

<video src="UPLOAD:batch-strip" controls muted></video>

## Try it

Ask your agent, with your own files:

```text
Make four versions of ./review.mp4, one per creator and place (a.jpg + cafe.jpg, b.jpg + car.jpg, ...). Keep the tumbler, the pitch and the timing.
```

## Plan

The four `plan-*.json` files are exactly what the agent submitted to ChatCut, with project-specific IDs removed. Image numbers in a plan refer to the reference images listed above, in that order.

## Source

The preview video of ChatCut's own "Cozy selfie product review" skill (AI-generated, 7–15 s).

## Notes

- The tumbler is a reference image too, so it keeps its exact colors in every version.
