import SwiftUI

struct RootView: View {
    @EnvironmentObject var store: GameStore
    @State private var filters = FilterState()
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            CatalogView(filters: $filters)
                .navigationTitle("Crossplay")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            showSettings = true
                        } label: {
                            Image(systemName: "gearshape")
                        }
                    }
                    ToolbarItem(placement: .topBarTrailing) {
                        Menu {
                            Button {
                                Task { await store.reloadFromServer() }
                            } label: {
                                Label("Fetch latest catalog", systemImage: "arrow.down.circle")
                            }
                            Button {
                                Task { await store.rebuildThenReload() }
                            } label: {
                                Label("Rebuild now (~2 min)", systemImage: "hammer")
                            }
                        } label: {
                            if case .loading = store.state {
                                ProgressView()
                            } else if case .rebuilding = store.state {
                                ProgressView()
                            } else {
                                Image(systemName: "arrow.clockwise")
                            }
                        }
                    }
                }
                .sheet(isPresented: $showSettings) {
                    SettingsView()
                }
                .overlay(alignment: .bottom) {
                    if case .rebuilding(let message) = store.state {
                        StatusBar(message: message, kind: .info)
                    } else if case .error(let msg) = store.state {
                        StatusBar(message: msg, kind: .error)
                            .onTapGesture { store.state = .idle }
                    }
                }
        }
    }
}

private struct StatusBar: View {
    enum Kind { case info, error }
    let message: String
    let kind: Kind

    var body: some View {
        HStack {
            if kind == .info {
                ProgressView().tint(.white)
            } else {
                Image(systemName: "exclamationmark.triangle.fill")
            }
            Text(message).font(.footnote)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(kind == .info ? Color.blue.opacity(0.9) : Color.red.opacity(0.9))
        .foregroundStyle(.white)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .padding(.bottom, 20)
        .padding(.horizontal)
        .shadow(radius: 6)
    }
}
