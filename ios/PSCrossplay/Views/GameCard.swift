import SwiftUI
import SafariServices

struct GameCard: View {
    let game: Game
    let showLabels: Bool
    @State private var showSafari = false

    var body: some View {
        Button {
            showSafari = true
        } label: {
            VStack(alignment: .leading, spacing: 6) {
                coverImage
                Text(game.title)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(2)
                if let year = game.releaseYear {
                    Text("\(year)").font(.caption2).foregroundStyle(.secondary)
                }
                if game.confidence == "medium" {
                    Text("· likely crossplay").font(.caption2).foregroundStyle(.orange)
                }
                if showLabels { labels }
            }
            .padding(8)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .overlay(alignment: .topTrailing) {
                if game.inExtra {
                    Text("PS+ Extra")
                        .font(.caption2.weight(.bold))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 3)
                        .background(Color.blue.opacity(0.9))
                        .foregroundStyle(.white)
                        .clipShape(Capsule())
                        .padding(8)
                }
            }
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showSafari) {
            SafariView(url: googleImagesURL)
                .ignoresSafeArea()
        }
    }

    @ViewBuilder
    private var coverImage: some View {
        let placeholder = RoundedRectangle(cornerRadius: 8).fill(Color.black.opacity(0.3))
        if let urlStr = game.backgroundImage, let url = URL(string: urlStr) {
            AsyncImage(url: url) { phase in
                switch phase {
                case .success(let img): img.resizable().scaledToFill()
                default: placeholder
                }
            }
            .frame(height: 90)
            .clipped()
            .clipShape(RoundedRectangle(cornerRadius: 8))
        } else {
            placeholder.frame(height: 90)
        }
    }

    @ViewBuilder
    private var labels: some View {
        FlowLayout(spacing: 4) {
            if let p = game.players {
                badge("\(p) players", bg: .blue.opacity(0.2), fg: .blue)
            }
            if game.onlineCoop == true {
                badge("Online co-op", bg: .green.opacity(0.2), fg: .green)
            }
            if game.splitscreen == true {
                badge("Splitscreen", bg: .orange.opacity(0.2), fg: .orange)
            }
            ForEach(game.crossplayPlatforms, id: \.self) { p in
                badge(p, bg: .teal.opacity(0.2), fg: .teal)
            }
            ForEach(game.viewTypes, id: \.self) { v in
                badge(v, bg: .pink.opacity(0.2), fg: .pink)
            }
            ForEach(game.genres.prefix(4), id: \.self) { g in
                badge(g, bg: .purple.opacity(0.2), fg: .purple)
            }
        }
    }

    private func badge(_ text: String, bg: Color, fg: Color) -> some View {
        Text(text)
            .font(.caption2)
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .background(bg)
            .foregroundStyle(fg)
            .clipShape(Capsule())
    }

    private var googleImagesURL: URL {
        var components = URLComponents(string: "https://www.google.com/search")!
        components.queryItems = [
            URLQueryItem(name: "tbm", value: "isch"),
            URLQueryItem(name: "q", value: "\(game.title) gameplay"),
        ]
        return components.url!
    }
}

private struct SafariView: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> SFSafariViewController {
        let vc = SFSafariViewController(url: url)
        vc.preferredControlTintColor = .white
        return vc
    }
    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {}
}

/// Simple flow layout — iOS 16+ has native FlowLayout via Layout protocol, but
/// this minimal implementation avoids the deployment-target dance.
struct FlowLayout: Layout {
    var spacing: CGFloat = 4

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var rowWidth: CGFloat = 0
        var rowHeight: CGFloat = 0
        var totalHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if rowWidth + size.width > maxWidth {
                totalHeight += rowHeight + spacing
                rowWidth = 0
                rowHeight = 0
            }
            rowWidth += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
        totalHeight += rowHeight
        return CGSize(width: maxWidth, height: totalHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX {
                x = bounds.minX
                y += rowHeight + spacing
                rowHeight = 0
            }
            view.place(at: CGPoint(x: x, y: y), proposal: .unspecified)
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}
