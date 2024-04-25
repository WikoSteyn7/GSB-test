import DOMPurify from 'dompurify';
import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import { Approaches, ChatResponse } from "../../api";

const CharacterStreamer = ({ finalAnswer, eventSource, nonEventString, onStreamingComplete, classNames, approach = Approaches.ChatWebRetrieveRead, typingSpeed = 30, setError }: 
  { finalAnswer?: (data: ChatResponse) => void; approach?: Approaches, eventSource?: any; nonEventString?: string, onStreamingComplete: any; classNames?: string; typingSpeed?: number; setError?: (error: string) => void; }) => {
  const [output, setOutput] = useState('');
  const queueRef = useRef<string[]>([]); // Now TypeScript knows this is an array of strings
  const processingRef = useRef(false);
  const [startUpData, setStartUpData] = useState({ data_points: [], web_citation_lookup: {}, work_citation_lookup: {}, thought_chain: {} });
  const isEndEventTriggered = useRef(false);
  const isLoading = useRef(true);
  const [dots, setDots] = useState('');
  const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

  const checkAndFinalizeAnswer = () => {
    //console.log('Checking final conditions', {
    //  processing: processingRef.current,
   //   queueLength: queueRef.current.length,
    //  endTriggered: isEndEventTriggered.current,
      // dataPoints: startUpData.data_points.length
    //});
    // Ensure all data is ready: processing finished, end event triggered, and startUpData loaded
    if (queueRef.current.length === 0 && isEndEventTriggered.current && (Object.keys(startUpData.web_citation_lookup).length > 0 || Object.keys(startUpData.work_citation_lookup).length > 0)) {
        if (finalAnswer) {
            finalAnswer({
                answer: output,
                thoughts: "",
                data_points: startUpData.data_points,
                approach: approach,
                web_citation_lookup: startUpData.web_citation_lookup,
                work_citation_lookup: startUpData.work_citation_lookup,
                thought_chain: startUpData.thought_chain
            });
            // console.log('Final answer sent with startup data:', startUpData);
        }
    }
  };

  useEffect(() => {
    // Close our event when the user attempts refresh or leaves the page
    const handleBeforeUnload = () => {
        eventSource?.close();
      };
  
      window.addEventListener('beforeunload', handleBeforeUnload);
  
      return () => {
        window.removeEventListener('beforeunload', handleBeforeUnload);
      };

}, []);

  useEffect(() => {
    const intervalId = setInterval(() => {
      setDots(prevDots => (prevDots.length < 3 ? prevDots + '.' : ''));
    }, 500); // Change dot every 500ms

    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, [isLoading.current]);

  useEffect(() => {
    checkAndFinalizeAnswer();
  }, [output]);

  useEffect(() => {
      chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" });
    }, [output]);
    

  useEffect(() => {
    if (!eventSource && nonEventString) {
        console.log("Event source not found");
        queueRef.current = queueRef.current.concat(nonEventString.split(''));
        if (!processingRef.current) {
            processQueue();
        }
    }
    const handleMessage = async (event: MessageEvent) => {
        // Process the Markdown content to HTML immediately
        //const processedHTML = await marked(event.data);
        // Split the processed HTML into an array of characters and add it to the queue
        // We use markdown, <br> does nothing for us. We need to replace it with \n
        const processedHTML = event.data.replace(/<br>/g, '\n');
        queueRef.current = queueRef.current.concat(processedHTML.split(''));
        // queueRef.current = queueRef.current.concat("\n\n");
        if (!processingRef.current) {
            processQueue();
        }
        isLoading.current = false;
    };

    const handleStartup = (event: MessageEvent) => {
        const startup = JSON.parse(event.data);
        console.log(event.data);
        setStartUpData({
            data_points: startup.data_points,
            web_citation_lookup: startup.web_citation_lookup,
            work_citation_lookup: startup.work_citation_lookup,
            thought_chain: startup.thought_chain
        });
        
    };

    const handleEnd = () => {
      isEndEventTriggered.current = true;
      if (onStreamingComplete) {
        onStreamingComplete(); // Call any additional cleanup or processes needed
      }
    };

    const handleError = (event: MessageEvent) => {
      if (setError){
        try {
          setError(JSON.parse(event.data).error);
        } catch (e) {
          setError(event.data); // If it's not JSON, just set the error message
        }
        eventSource.close();
      }
    }

    if (eventSource) {
      eventSource.addEventListener('error', handleError);
      eventSource.addEventListener('startup', handleStartup);
      eventSource.addEventListener('message', handleMessage);
      eventSource.addEventListener('end', handleEnd);
    }

    return () => {
      if (eventSource) {
        eventSource.removeEventListener('error', handleError);
        eventSource.removeEventListener('startup', handleStartup);
        eventSource.removeEventListener('message', handleMessage);
        eventSource.removeEventListener('end', handleEnd);
      }
    };
  }, [eventSource, nonEventString]);

  const processQueue = () => {
    processingRef.current = true;
    const intervalId = setInterval(() => {
      if (queueRef.current.length > 0) {
        const char = queueRef.current.shift();
        setOutput((prevOutput) => {
            const updatedOutput = prevOutput + char;
            return updatedOutput;
        });
      } else {
        processingRef.current = false;
        isLoading.current = true;
        checkAndFinalizeAnswer();
        clearInterval(intervalId);
      }
    }, typingSpeed); // Adjust based on desired "typing" speed
  };

  if (isLoading.current && !output) {
    return <div className={classNames}>Generating Answer{dots}</div>;
  }

  return <div className={classNames}><ReactMarkdown children={output} rehypePlugins={[rehypeRaw, rehypeSanitize]}></ReactMarkdown>
   <div ref={chatMessageStreamEnd} />
  </div>;

};

export default CharacterStreamer;
