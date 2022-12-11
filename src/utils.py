from gi.repository import Gst, Gdk
import sys
import xml

class Utils():

    # the highest range in decibels there can be between any two levels
    DECIBEL_RANGE = 80

    NANO_TO_MILLI_DIVISOR = Gst.SECOND / 1000

    @classmethod
    def store_parameters_to_xml(cls, project, doc, parent, parameters):
        """
        Saves the variables indicated by the parameters in an XML document.

        Parameters:
        doc -- name of the XML document to save the settings into.
        parent -- XML parent tag to use in doc.
        parameters -- list of variable names whose value, save in doc.
        """
        for param in parameters:
            node = doc.createElement(param)
            cls.store_variable_to_node(getattr(project, param), node)
            parent.appendChild(node)

    @classmethod
    def store_variable_to_node(cls, value, node, typeAttr="type", valueAttr="value"):
        """
        Saves a variable to an specific XML node.

        Example:
            typeAttr = "foo"
            valueAttr = "bar"
            value = "mystring"

            would result in the following XML code:
                <foo="str" bar="mystring" />

        Parameters:
            value -- the value of the variable.
            node -- node to save the variable value to.
            typeAttr -- type of the variable to be saved.
            valueAttr -- value of the variable to be loaded.
        """
        if type(value) == int:
            node.setAttribute(typeAttr, "int")
        elif type(value) == float:
            node.setAttribute(typeAttr, "float")
        elif type(value) == bool:
            node.setAttribute(typeAttr, "bool")
        elif value == None:
            node.setAttribute(typeAttr, "NoneType")
        else:
            node.setAttribute(typeAttr, "str")
        node.setAttribute(valueAttr, str(value))

    @classmethod
    def CalculateAudioLevelFromStructure(cls, structure):
        """
        Calculates an average for all channel levels.

        Parameters:
            channelLevels -- list of levels from each channel.

        Returns:
            an average level, also taking into account negative infinity numbers,
            which will be discarded in the average.
        """
        # FIXME: currently everything is being averaged to a single channel
        channelLevels = structure.get_value("rms")

        negInf = -1E+5000
        peaktotal = 0
        for peak in channelLevels:
            print(peak)
            #if peak > 0.001:
            #    print channelLevels
            #don't add -inf values cause 500 + -inf is still -inf
            if peak != negInf:
                peaktotal += peak
            else:
                peaktotal -= cls.DECIBEL_RANGE

        peaktotal /= len(channelLevels)

        peaktotal += cls.DECIBEL_RANGE
        #convert to an integer
        peaktotal = min(peaktotal, cls.DECIBEL_RANGE)
        peaktotal = max(peaktotal, -cls.DECIBEL_RANGE)
        peakint = int((peaktotal / cls.DECIBEL_RANGE) * sys.maxsize)

        endtime = structure.get_value("endtime")
        #convert number from Gst.SECOND (i.e. nanoseconds) to milliseconds
        endtime_millis = int(endtime / cls.NANO_TO_MILLI_DIVISOR)

        return (endtime_millis, [peakint])

    @classmethod
    def GdkRectangle(cls, x, y, width, height):
        # convenience constructor for GdkRectangle struct.
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        rect.width = width
        rect.height = height

        return rect

    @classmethod
    def GdkRectangleAsTuple(cls, rect):
        return (rect.x, rect.y, rect.width, rect.height)

    @classmethod
    def load_params_from_xml(cls, obj, parentElement):
        """
        Loads parameters from an XML and fills variables of the same name
        in that module.

        Parameters:
            parentElement -- block of XML with the parameters.
        """
        for node in parentElement.childNodes:
            if node.nodeType == xml.dom.Node.ELEMENT_NODE:
                value = cls.load_variable_from_node(node)
                setattr(obj, node.tagName, value)

    @classmethod
    def load_variable_from_node(cls, node, typeAttr="type", valueAttr="value"):
        """
        Loads a variable from an specific XML node.

        Example:
            Please refer to the StoreVariableToNode example
            for the explanation of the typeAttr and valueAttr
            parameters.

        Parameters:
            node -- node from which the variable is loaded.
            typeAttr -- string of the attribute name that the
                        variable's type will be saved under.
            valueAttr -- string of the attribute name that the
                        variable's value will be saved under.

        Returns:
            the loaded variable.
        """
        if node.getAttribute(typeAttr) == "int":
            variable = int(node.getAttribute(valueAttr))
        elif node.getAttribute(typeAttr) == "float":
            variable = float(node.getAttribute(valueAttr))
        elif node.getAttribute(typeAttr) == "bool":
            variable = (node.getAttribute(valueAttr) == "True")
        elif node.getAttribute(typeAttr) == "NoneType":
            variable = None
        else:
            variable = node.getAttribute(valueAttr)

        return variable

    @classmethod
    def store_params_to_xml(cls, obj, doc, parent, parameters):
        """
        Saves the variables indicated by the parameters in an XML document.

        Parameters:
            doc -- name of the XML document to save the settings into.
            parent -- XML parent tag to use in doc.
            parameters -- list of variable names whose value, save in doc.
        """
        for param in parameters:
            node = doc.createElement(param)
            cls.store_variable_to_node(getattr(obj, param), node)
            parent.appendChild(node)

    @classmethod
    def store_dictionary_to_xml(cls, doc, parent, dict, tagName=None):
        """
        Saves a dictionary of settings in an XML document.

        Parameters:
            doc -- name of the XML document to save the settings into.
            parent -- XML parent tag to use in doc.
            dict -- dictionary to be saved in doc.
            tagName -- name used for all tag names.

        Considerations:
            If tagName is not given, the dictionary keys will be used for the tag names.
            This means that the keys must all be strings and can't have any invalid XML
            characters in them.
            If tagName is given, it is used for all the tag names, and the key is stored
            in the keyvalue attribute and its type in the keytype attribute.
        """
        for key, value in dict.items():
            if tagName:
                node = doc.createElement(tagName)
                cls.store_variable_to_node(key, node, "keytype", "keyvalue")
            #if no tag name was provided, use the key
            else:
                node = doc.createElement(key)

            cls.store_variable_to_node(value, node, "type", "value")
            parent.appendChild(node)

    @classmethod
    def store_variable_to_node(cls, value, node, typeAttr="type", valueAttr="value"):
        """
        Saves a variable to an specific XML node.

        Example:
            typeAttr = "foo"
            valueAttr = "bar"
            value = "mystring"

            would result in the following XML code:
                <foo="str" bar="mystring" />

        Parameters:
            value -- the value of the variable.
            node -- node to save the variable value to.
            typeAttr -- type of the variable to be saved.
            valueAttr -- value of the variable to be loaded.
        """
        if type(value) == int:
            node.setAttribute(typeAttr, "int")
        elif type(value) == float:
            node.setAttribute(typeAttr, "float")
        elif type(value) == bool:
            node.setAttribute(typeAttr, "bool")
        elif value == None:
            node.setAttribute(typeAttr, "NoneType")
        else:
            node.setAttribute(typeAttr, "str")

        node.setAttribute(valueAttr, str(value))

    @classmethod
    def load_dictionary_from_xml(cls, parentElement):
        """
        For those times when you don't want to fill module variables with
        parameters from the XML but just want to fill a dictionary instead.

        Parameters:
            parentElement -- XML element from which the dictionary is loaded.

        Returns:
            a dictionary with the loaded values in (type, value) format.
        """
        dictionary = {}

        for node in parentElement.childNodes:
            if node.nodeType == xml.minidom.Node.ELEMENT_NODE:
                if node.hasAttribute("keytype") and node.hasAttribute("keyvalue"):
                    key = cls.load_variable_from_node(node, "keytype", "keyvalue")
                else:
                    key = node.tagName
                value = cls.load_variable_from_node(node, "type", "value")
                dictionary[key] = value
