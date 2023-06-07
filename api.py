import wave

from collections.abc import AsyncIterable

from quart import Quart, request, jsonify

from wyoming.asr import Transcript
from wyoming.client import AsyncTcpClient
from wyoming.audio import AudioChunk, AudioStart, AudioStop

app = Quart(__name__)

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
SAMPLE_CHANNELS = 1


@app.route('/', methods=['POST'])
async def index():
    print("Incoming")
    byte_array = request.body

    resp, good = await async_process_audio_stream(byte_array)

    resp = resp.replace("%", " percent")
    print("Response: " + resp)

    return jsonify({"text": resp})


async def async_process_audio_stream(stream: AsyncIterable[bytes]):
    text = None
    try:
        async with AsyncTcpClient("10.0.0.10", 10300) as client:
            await client.write_event(
                AudioStart(
                    rate=SAMPLE_RATE,
                    width=SAMPLE_WIDTH,
                    channels=SAMPLE_CHANNELS,
                ).event(),
            )

            async for audio_bytes in stream:
                chunk = AudioChunk(
                    rate=SAMPLE_RATE,
                    width=SAMPLE_WIDTH,
                    channels=SAMPLE_CHANNELS,
                    audio=audio_bytes,
                )
                await client.write_event(chunk.event())

            await client.write_event(AudioStop().event())

            while True:
                event = await client.read_event()
                if event is None:
                    print("that did not work")

                if Transcript.is_type(event.type):
                    transcript = Transcript.from_event(event)
                    text = transcript.text
                    break

    except Exception as err:
        print("Error processing audio stream: %s", err)

    return (
        text,
        True,
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9878)
