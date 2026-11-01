import SwiftUI

/// The video a quote was taken from: its thumbnail, the moment it was said and a
/// tap that opens YouTube at exactly that second. Shown only for statements read
/// from a partner channel's captions, labelled as automatic captions so a reader
/// knows to check a word against the video.
struct VideoMomentCard: View {
    let statement: Statement
    var compact = false

    var body: some View {
        if let url = URL(string: statement.url), let thumb = statement.videoThumbnailURL {
            Link(destination: url) {
                VStack(alignment: .leading, spacing: 8) {
                    ZStack {
                        AsyncImage(url: thumb) { phase in
                            if case .success(let image) = phase {
                                image.resizable().scaledToFill()
                            } else {
                                Rectangle().fill(SDTheme.panel2)
                            }
                        }
                        LinearGradient(colors: [.clear, .black.opacity(0.55)], startPoint: .center, endPoint: .bottom)
                        Image(systemName: "play.fill")
                            .font(.system(size: compact ? 16 : 20, weight: .bold))
                            .foregroundStyle(.white)
                            .frame(width: compact ? 40 : 52, height: compact ? 40 : 52)
                            .background(Circle().fill(.black.opacity(0.55)))
                        if let moment = statement.videoMoment {
                            Text(moment)
                                .font(.caption.weight(.bold).monospacedDigit())
                                .foregroundStyle(.white)
                                .padding(.horizontal, 7).padding(.vertical, 3)
                                .background(Capsule().fill(.black.opacity(0.75)))
                                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottomTrailing)
                                .padding(8)
                        }
                    }
                    .aspectRatio(16 / 9, contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(RoundedRectangle(cornerRadius: 12).stroke(SDTheme.line, lineWidth: 1))

                    HStack(spacing: 6) {
                        Image(systemName: "captions.bubble").font(.caption2)
                        Text("Videodan · otomatik altyazı").font(.caption2.weight(.semibold))
                        Spacer(minLength: 0)
                        if let moment = statement.videoMoment {
                            Text("\(moment) anından izle").font(.caption2.weight(.bold)).foregroundStyle(SDTheme.accent)
                        }
                    }
                    .foregroundStyle(SDTheme.muted)
                }
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Videoyu \(statement.videoMoment ?? "baştan") anından aç")
        }
    }
}
