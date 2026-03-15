/* NeuronOS Installation Slideshow */

import QtQuick 2.15
import calamares.slideshow 1.0

Presentation {
    id: presentation

    Timer {
        interval: 15000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        anchors.fill: parent
        anchors.verticalCenterOffset: 0

        Rectangle {
            anchors.fill: parent
            color: "#1a1a2e"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -80
            text: "Welcome to NeuronOS"
            font.pixelSize: 48
            font.bold: true
            color: "#ffffff"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 20
            text: "The desktop operating system designed to run\nall your applications — Windows, Linux, and more."
            font.pixelSize: 24
            color: "#cccccc"
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Slide {
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#1a1a2e"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -80
            text: "Seamless Windows Applications"
            font.pixelSize: 42
            font.bold: true
            color: "#ffffff"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 20
            text: "Run Adobe Creative Suite, AutoCAD, SolidWorks,\nand more — directly on your Linux desktop.\n\nNo dual-boot. No compromises."
            font.pixelSize: 20
            color: "#cccccc"
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Slide {
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#1a1a2e"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -80
            text: "GPU-Accelerated Performance"
            font.pixelSize: 42
            font.bold: true
            color: "#ffffff"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 20
            text: "Your graphics card powers Windows applications\nwith near-native performance.\n\n98% of bare metal speed for GPU-intensive work."
            font.pixelSize: 20
            color: "#cccccc"
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Slide {
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#1a1a2e"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -80
            text: "It Just Works"
            font.pixelSize: 42
            font.bold: true
            color: "#ffffff"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 20
            text: "NeuronOS automatically configures everything:\n• GPU passthrough\n• Hardware detection\n• Application routing\n\nClick an icon. The app opens. That's it."
            font.pixelSize: 20
            color: "#cccccc"
            horizontalAlignment: Text.AlignHCenter
        }
    }

    Slide {
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#1a1a2e"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: -80
            text: "Almost there..."
            font.pixelSize: 42
            font.bold: true
            color: "#ffffff"
        }

        Text {
            anchors.centerIn: parent
            anchors.verticalCenterOffset: 20
            text: "Installation is almost complete.\nYour system will restart when finished.\n\nThank you for choosing NeuronOS!"
            font.pixelSize: 20
            color: "#cccccc"
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
