param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$request = Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8 | ConvertFrom-Json
# This fixed, reviewed helper captures callbacks on the synthesizer thread.
# Input remains plain text; no input is interpolated into C# or SSML.
Add-Type -ReferencedAssemblies ([System.Speech.Synthesis.SpeechSynthesizer].Assembly.Location) -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Speech.Synthesis;
using System.Speech.AudioFormat;
public sealed class TldrSpeechMark {
    public double seconds;
    public int character_position;
    public int character_count;
    public string text;
}
public sealed class TldrSpeechResult {
    public string voice;
    public List<TldrSpeechMark> marks = new List<TldrSpeechMark>();
}
public static class TldrSpeech {
    public static TldrSpeechResult Write(string text, string path, int rate) {
        var result = new TldrSpeechResult();
        using (var speaker = new SpeechSynthesizer()) {
            speaker.Rate = rate;
            result.voice = speaker.Voice.Name;
            speaker.SpeakProgress += delegate(object sender, SpeakProgressEventArgs e) {
                lock (result.marks) {
                    result.marks.Add(new TldrSpeechMark {
                        seconds = e.AudioPosition.TotalSeconds,
                        character_position = e.CharacterPosition,
                        character_count = e.CharacterCount,
                        text = e.Text
                    });
                }
            };
            speaker.SetOutputToWaveFile(path, new SpeechAudioFormatInfo(16000, AudioBitsPerSample.Sixteen, AudioChannel.Mono));
            speaker.Speak(text);
        }
        return result;
    }
}
'@
$result = [TldrSpeech]::Write([string]$request.text, [string]$request.path, [int]$request.rate)
$json = $result | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText([string]$request.marks_path, $json, (New-Object System.Text.UTF8Encoding($false)))
