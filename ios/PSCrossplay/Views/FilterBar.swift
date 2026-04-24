import SwiftUI

struct FilterState: Equatable {
    var search: String = ""
    var genre: String = ""        // empty = "All"
    var view: String = ""         // empty = "Any perspective"
    var showLabels: Bool = false
    var strictOnly: Bool = false
}

struct FilterBar: View {
    @Binding var filters: FilterState
    let allGenres: [String]
    let allViews: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                TextField("Filter by title…", text: $filters.search)
                    .textFieldStyle(.plain)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                if !filters.search.isEmpty {
                    Button { filters.search = "" } label: {
                        Image(systemName: "xmark.circle.fill").foregroundStyle(.secondary)
                    }
                }
            }
            .padding(10)
            .background(Color(.secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 10))

            HStack(spacing: 10) {
                Menu {
                    Picker("Genre", selection: $filters.genre) {
                        Text("All genres").tag("")
                        ForEach(allGenres, id: \.self) { Text($0).tag($0) }
                    }
                } label: {
                    menuLabel(icon: "line.3.horizontal.decrease", text: filters.genre.isEmpty ? "Genre" : filters.genre)
                }
                Menu {
                    Picker("Perspective", selection: $filters.view) {
                        Text("Any perspective").tag("")
                        ForEach(allViews, id: \.self) { Text($0).tag($0) }
                    }
                } label: {
                    menuLabel(icon: "eye", text: filters.view.isEmpty ? "Perspective" : filters.view)
                }
                Spacer()
            }

            HStack(spacing: 14) {
                Toggle(isOn: $filters.showLabels) {
                    Label("Labels", systemImage: "tag")
                }
                .toggleStyle(.button)
                .buttonStyle(.bordered)

                Toggle(isOn: $filters.strictOnly) {
                    Label("High-conf", systemImage: "checkmark.seal")
                }
                .toggleStyle(.button)
                .buttonStyle(.bordered)
            }
        }
    }

    private func menuLabel(icon: String, text: String) -> some View {
        Label(text, systemImage: icon)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color(.secondarySystemBackground))
            .clipShape(Capsule())
            .foregroundStyle(.primary)
    }
}
